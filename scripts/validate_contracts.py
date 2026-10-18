"""Contract checks for contracts/ (dev tool; requires jsonschema, pyyaml, openapi-spec-validator).

Checks:
  1. Every JSON Schema in contracts/ is a valid Draft 2020-12 schema.
  2. Examples validate against their schemas (capabilities, workflows, rule packs, LLM profiles).
  3. Embedded capability schemas are valid and contain no non-local $ref.
  4. Workflows: pinned id@version exists, node config matches configuration_schema, edges/inputs map to
     declared fields, every required node input is fed, outputs exist, the graph is acyclic,
     referenced rule packs exist.
  5. openapi.yaml is a valid OpenAPI 3.1 document.
  6. Scenario words do not appear in generic engine modules (when backend/ exists).

Usage: python scripts/validate_contracts.py
"""

from __future__ import annotations

import json
import re
import sys
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"
EXAMPLES = CONTRACTS / "examples"
ENGINE_DIRS = ["catalog", "composer", "executor", "adapters", "evaluation", "observability", "reuse"]
SCENARIO_WORDS = re.compile(r"invoice|contract_review|請求書|契約書")  # 契約 alone also means "capability contract"
ALLOWED_ROLES = {"public", "any_authenticated", "project_member", "admin",
                 "solution_lead", "solution_architect", "qa_evaluator", "business_reviewer"}
PUBLIC_ROUTES = {"/health", "/ready", "/api/v1/session"}

errors: list[str] = []


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.suffix in (".yaml", ".yml") else json.loads(text)


def check(validator: Draft202012Validator, instance, label: str) -> None:
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        errors.append(f"{label}: {'/'.join(map(str, err.path)) or '(root)'}: {err.message}")


def external_refs(node, path="") -> list[str]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and not value.startswith("#"):
                found.append(f"{path}/$ref={value}")
            found += external_refs(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += external_refs(value, f"{path}/{i}")
    return found


def null_keys(node, path="") -> list[str]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if value is None:
                found.append(f"{path}/{key}")
            found += null_keys(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += null_keys(value, f"{path}/{i}")
    return found


def root_property(pointer: str) -> str:
    return pointer.split("/")[1]


def main() -> int:
    schemas = {p.name.removesuffix(".schema.json"): load(p) for p in CONTRACTS.glob("*.schema.json")}
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001 - report every invalid schema
            errors.append(f"{name}.schema.json: invalid schema: {exc}")
    validators = {name: Draft202012Validator(s) for name, s in schemas.items()}

    capabilities = {}
    for path in sorted((EXAMPLES / "capabilities").glob("*.json")):
        cap = load(path)
        check(validators["capability"], cap, path.name)
        for key in ("input_schema", "output_schema", "configuration_schema"):
            try:
                Draft202012Validator.check_schema(cap[key])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path.name}: {key} is not a valid schema: {exc}")
        for ref in external_refs(cap):
            errors.append(f"{path.name}: external $ref is not allowed: {ref}")
        capabilities[f"{cap['capability_id']}@{cap['version']}"] = cap

    rule_packs = {}
    for path in sorted((EXAMPLES / "rule_packs").glob("*.json")):
        pack = load(path)
        check(validators["rule_pack"], pack, path.name)
        rule_ids = [r["rule_id"] for r in pack["rules"]]
        if len(rule_ids) != len(set(rule_ids)):
            errors.append(f"{path.name}: duplicate rule_id")
        rule_packs[f"{pack['rule_pack_id']}@{pack['version']}"] = pack

    for path in sorted((EXAMPLES / "workflows").glob("*.json")):
        wf = load(path)
        check(validators["workflow"], wf, path.name)
        nodes = {n["node_id"]: n for n in wf["nodes"]}
        if len(nodes) != len(wf["nodes"]):
            errors.append(f"{path.name}: duplicate node_id")
        fed: dict[str, set[str]] = {node_id: set() for node_id in nodes}
        node_caps = {}
        for node_id, node in nodes.items():
            key = f"{node['capability_id']}@{node['capability_version']}"
            cap = capabilities.get(key)
            if cap is None:
                errors.append(f"{path.name}: node {node_id}: unknown capability version {key}")
                continue
            node_caps[node_id] = cap
            check(Draft202012Validator(cap["configuration_schema"]), node["config"], f"{path.name}: node {node_id} config")
            if "rule_pack_id" in node["config"]:
                pack_key = f"{node['config']['rule_pack_id']}@{node['config']['rule_pack_version']}"
                if pack_key not in rule_packs:
                    errors.append(f"{path.name}: node {node_id}: unknown rule pack {pack_key}")
            if node.get("timeout_ms", 0) > cap["timeout_ms"]:
                errors.append(f"{path.name}: node {node_id}: timeout_ms exceeds capability limit")
        for item in wf["inputs"]:
            for target in item["to"]:
                fed.setdefault(target["node_id"], set()).add(target["field"])
        graph: dict[str, set[str]] = {node_id: set() for node_id in nodes}
        for edge in wf["edges"]:
            if edge["from"] not in nodes or edge["to"] not in nodes:
                errors.append(f"{path.name}: edge {edge['from']}->{edge['to']}: unknown node")
                continue
            graph[edge["to"]].add(edge["from"])
            src, dst = node_caps.get(edge["from"]), node_caps.get(edge["to"])
            if src is None or dst is None:  # unknown capability version already reported
                continue
            for m in edge["mapping"]:
                if root_property(m["from_path"]) not in src["output_schema"]["properties"]:
                    errors.append(f"{path.name}: edge {edge['from']}->{edge['to']}: {m['from_path']} not in output_schema")
                if m["to_field"] not in dst["input_schema"]["properties"]:
                    errors.append(f"{path.name}: edge {edge['from']}->{edge['to']}: {m['to_field']} not in input_schema")
                fed[edge["to"]].add(m["to_field"])
        for node_id, cap in node_caps.items():
            missing = set(cap["input_schema"].get("required", [])) - fed[node_id]
            if missing:
                errors.append(f"{path.name}: node {node_id}: required inputs not fed: {sorted(missing)}")
        for out in wf["outputs"]:
            cap = node_caps.get(out["from_node"])
            if cap is None or root_property(out["from_path"]) not in cap["output_schema"]["properties"]:
                errors.append(f"{path.name}: output {out['name']}: invalid source")
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            errors.append(f"{path.name}: cycle detected: {exc.args[1]}")

    profiles_path = EXAMPLES / "llm_profiles.example.yaml"
    check(validators["llm_profile"], load(profiles_path), profiles_path.name)

    openapi = load(CONTRACTS / "openapi.yaml")
    try:
        validate_openapi(openapi)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"openapi.yaml: {exc}")
    # Every operation declares who may call it (docs/design/basic/permissions.md).
    for route, item in openapi.get("paths", {}).items():
        for method, op in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            declared = op.get("x-easf-roles")
            if not declared or not set(declared) <= ALLOWED_ROLES:
                errors.append(f"openapi.yaml: {method.upper()} {route}: x-easf-roles missing or invalid: {declared}")
            elif "public" in declared and route not in PUBLIC_ROUTES:
                errors.append(f"openapi.yaml: {method.upper()} {route}: public is allowed only for {sorted(PUBLIC_ROUTES)}")
    # An unquoted comma inside a YAML flow mapping silently turns prose into null-valued keys.
    for pointer in null_keys(openapi):
        errors.append(f"openapi.yaml: null-valued key (unquoted comma in flow mapping?): {pointer}")

    for module in ENGINE_DIRS:
        for py in (ROOT / "backend" / "app" / module).rglob("*.py"):
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if SCENARIO_WORDS.search(line):
                    errors.append(f"{py.relative_to(ROOT)}:{lineno}: scenario word in generic engine module")

    if errors:
        print("\n".join(errors))
        print(f"NG: {len(errors)} 件")
        return 1
    print(f"OK: schemas={len(schemas)} capabilities={len(capabilities)} rule_packs={len(rule_packs)} "
          f"workflows={len(list((EXAMPLES / 'workflows').glob('*.json')))} openapi=valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
