"""Contract validation at registration time (schema + rules the schema cannot express)."""

import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import rfc8785
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from app.catalog.registry import is_allowed

MAX_EXPR_DEPTH = 8


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    location: str


def contracts_dir() -> Path:
    return Path(os.environ.get("EASF_CONTRACTS_DIR") or Path(__file__).resolve().parents[3] / "contracts")


@lru_cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((contracts_dir() / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def content_sha256(document: dict[str, Any]) -> str:
    """SHA-256 of the RFC 8785 canonical JSON (ADR-004): key order and whitespace do not matter."""
    return hashlib.sha256(rfc8785.dumps(document)).hexdigest()


def schema_issues(name: str, document: Any) -> list[Issue]:
    return [
        Issue("schema_violation", err.message[:300], "/" + "/".join(str(p) for p in err.absolute_path))
        for err in sorted(_validator(name).iter_errors(document), key=lambda e: list(map(str, e.absolute_path)))[:100]
    ]


def _external_refs(node: Any, path: str = "") -> list[Issue]:
    found: list[Issue] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("$ref", "$dynamicRef") and not (isinstance(value, str) and value.startswith("#")):
                found.append(Issue("external_ref", "外部を参照する $ref は使えません。", f"{path}/{key}"))
            found += _external_refs(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += _external_refs(value, f"{path}/{i}")
    return found


def validate_capability(contract: Any) -> list[Issue]:
    issues = schema_issues("capability", contract)
    if not isinstance(contract, dict) or issues:
        return issues
    issues += _external_refs(contract)
    for key in ("input_schema", "output_schema", "configuration_schema"):
        try:
            Draft202012Validator.check_schema(contract[key])
        except SchemaError as exc:
            issues.append(Issue("invalid_embedded_schema", exc.message[:300], f"/{key}"))
    if not is_allowed(contract["kind"], contract["implementation"]["ref"]):
        issues.append(Issue("unknown_implementation", "許可されていない実装の参照です。", "/implementation/ref"))
    return issues


def _depth(expr: Any) -> int:
    if not isinstance(expr, dict):
        return 0
    children = list(expr.get("args", [])) + ([expr["arg"]] if "arg" in expr else [])
    return 1 + max((_depth(c) for c in children), default=0)


def validate_rule_pack(pack: Any) -> list[Issue]:
    issues = schema_issues("rule_pack", pack)
    if not isinstance(pack, dict) or issues:
        return issues
    tables = set(pack.get("reference_tables", {}))
    seen: set[str] = set()
    for i, rule in enumerate(pack["rules"]):
        if rule["rule_id"] in seen:
            issues.append(Issue("duplicate_rule_id", "rule_id が重複しています。", f"/rules/{i}/rule_id"))
        seen.add(rule["rule_id"])
        if _depth(rule["check"]) > MAX_EXPR_DEPTH:
            issues.append(
                Issue("expression_too_deep", f"式の入れ子は {MAX_EXPR_DEPTH} 段までです。", f"/rules/{i}/check")
            )
        for j, table in enumerate(_tables_used(rule["check"])):
            if table not in tables:
                issues.append(Issue("unknown_reference_table", "定義されていない参照表です。", f"/rules/{i}/check/{j}"))
    return issues


def _tables_used(expr: Any) -> list[str]:
    if not isinstance(expr, dict):
        return []
    used = [expr["table"]] if expr.get("op") == "matches_reference" else []
    for child in list(expr.get("args", [])) + ([expr["arg"]] if "arg" in expr else []):
        used += _tables_used(child)
    return used
