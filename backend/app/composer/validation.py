"""Composer: static validation of a Workflow against the pinned Capability contracts (run_execution.md §2).

This is the second of the three schema checks (registration, composition, execution). It knows nothing about
any business domain: everything comes from the workflow document and the registered contracts.
"""

import graphlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from app.catalog.registry import IMPLEMENTATIONS
from app.catalog.validation import Issue, schema_issues

# Workflow input types and the JSON Schema types they deliver to a node field.
INPUT_TYPES: dict[str, set[str]] = {
    "document_ref": {"string"},
    "string": {"string"},
    "integer": {"integer"},
    "boolean": {"boolean"},
}
HUMAN_REVIEW_KEY = ("local", "human_review.v1")

ContractLookup = Callable[[str, str], dict[str, Any] | None]
"""(capability_id, version) -> the registered contract, or None."""


@dataclass
class Report:
    errors: list[Issue]
    warnings: list[Issue]

    @property
    def valid(self) -> bool:
        return not self.errors


def _types(schema: dict[str, Any] | None) -> set[str] | None:
    """JSON Schema types a (sub)schema allows; None when it does not say (not checked statically)."""
    if not isinstance(schema, dict):
        return None
    declared = schema.get("type")
    if isinstance(declared, str):
        return {declared}
    if isinstance(declared, list):
        return {t for t in declared if isinstance(t, str)}
    if "enum" in schema and isinstance(schema["enum"], list):
        return {_json_type(v) for v in schema["enum"]}
    if "const" in schema:
        return {_json_type(schema["const"])}
    return None


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return "array" if isinstance(value, list) else "object"


def _compatible(source: set[str] | None, target: set[str] | None) -> bool:
    if source is None or target is None:
        return True  # checked at run time against the input schema
    widened = target | ({"integer"} if "number" in target else set())
    return source <= widened


def resolve_pointer(schema: dict[str, Any], pointer: str) -> dict[str, Any] | None:
    """Sub-schema that a JSON Pointer reaches inside instances of `schema`; None if it cannot exist."""
    current: Any = schema
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict):
            return None
        if token in current.get("properties", {}):
            current = current["properties"][token]
        elif token.isdigit() and isinstance(current.get("items"), dict):
            current = current["items"]
        elif isinstance(current.get("additionalProperties"), dict):
            current = current["additionalProperties"]
        else:
            return None
    return current if isinstance(current, dict) else None


def validate_workflow(workflow: Any, lookup: ContractLookup) -> Report:
    report = Report(errors=schema_issues("workflow", workflow), warnings=[])
    if report.errors or not isinstance(workflow, dict):
        return report
    errors, warnings = report.errors, report.warnings

    nodes: dict[str, dict[str, Any]] = {}
    for i, node in enumerate(workflow["nodes"]):
        if node["node_id"] in nodes:
            errors.append(Issue("duplicate_node", "node_id が重複しています。", f"/nodes/{i}/node_id"))
        nodes[node["node_id"]] = node

    contracts: dict[str, dict[str, Any]] = {}
    for i, node in enumerate(workflow["nodes"]):
        contract = lookup(node["capability_id"], node["capability_version"])
        if contract is None:
            errors.append(Issue("unknown_capability_version", "登録されていない Capability の版です。", f"/nodes/{i}"))
            continue
        contracts[node["node_id"]] = contract
        impl = IMPLEMENTATIONS.get((contract["kind"], contract["implementation"]["ref"]))
        if impl is None or not impl.available:
            warnings.append(
                Issue(
                    "implementation_unavailable",
                    "この Capability の実装はまだ利用できません。検証と承認はできますが、実行はできません。",
                    f"/nodes/{i}",
                )
            )
        for err in Draft202012Validator(contract["configuration_schema"]).iter_errors(node["config"]):
            location = "/".join(str(p) for p in err.absolute_path)
            errors.append(
                Issue("config_schema", err.message[:300], f"/nodes/{i}/config" + (f"/{location}" if location else ""))
            )
        if node.get("timeout_ms", 0) > contract["timeout_ms"]:
            errors.append(
                Issue(
                    "timeout_exceeds_capability",
                    "timeout_ms が Capability の上限を超えています。",
                    f"/nodes/{i}/timeout_ms",
                )
            )

    def check_node_ref(node_id: str, location: str) -> bool:
        if node_id not in nodes:
            errors.append(Issue("unknown_node", "存在しないノードを参照しています。", location))
            return False
        return True

    # field deliveries: (target node, field) -> list of (source types, location)
    delivered: dict[tuple[str, str], list[str]] = {}
    sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter({n: set() for n in nodes})
    fed: set[str] = set()

    for i, item in enumerate(workflow["inputs"]):
        for j, target in enumerate(item["to"]):
            location = f"/inputs/{i}/to/{j}"
            if not check_node_ref(target["node_id"], location):
                continue
            fed.add(target["node_id"])
            delivered.setdefault((target["node_id"], target["field"]), []).append(location)
            _check_field(contracts, target["node_id"], target["field"], INPUT_TYPES[item["type"]], location, errors)

    for i, edge in enumerate(workflow["edges"]):
        ok_from = check_node_ref(edge["from"], f"/edges/{i}/from")
        ok_to = check_node_ref(edge["to"], f"/edges/{i}/to")
        if not (ok_from and ok_to):
            continue
        sorter.add(edge["to"], edge["from"])
        fed.add(edge["to"])
        for j, mapping in enumerate(edge["mapping"]):
            location = f"/edges/{i}/mapping/{j}"
            delivered.setdefault((edge["to"], mapping["to_field"]), []).append(location)
            source_types: set[str] | None = None
            if edge["from"] in contracts:
                sub = resolve_pointer(contracts[edge["from"]]["output_schema"], mapping["from_path"])
                if sub is None:
                    errors.append(
                        Issue("unknown_output_path", "出力に存在しない項目を参照しています。", f"{location}/from_path")
                    )
                    continue
                source_types = _types(sub)
            _check_field(contracts, edge["to"], mapping["to_field"], source_types, location, errors)

    try:
        sorter.prepare()
    except graphlib.CycleError:
        errors.append(Issue("cycle", "ノードのつながりが循環しています。", "/edges"))

    for (_node_id, field), locations in delivered.items():
        if len(locations) > 1:
            errors.append(Issue("duplicate_input", f"入力 {field} が複数の経路から渡されています。", locations[1]))
    for i, node in enumerate(workflow["nodes"]):
        node_id = node["node_id"]
        if node_id not in fed:
            errors.append(Issue("unreachable_node", "入力も辺もつながっていないノードです。", f"/nodes/{i}"))
        contract = contracts.get(node_id)
        if contract is None:
            continue
        for field in contract["input_schema"].get("required", []):
            if (node_id, field) not in delivered:
                errors.append(Issue("missing_input", f"必須の入力 {field} が渡されていません。", f"/nodes/{i}"))

    for i, output in enumerate(workflow["outputs"]):
        location = f"/outputs/{i}"
        if check_node_ref(output["from_node"], f"{location}/from_node") and output["from_node"] in contracts:
            schema = contracts[output["from_node"]]["output_schema"]
            if resolve_pointer(schema, output["from_path"]) is None:
                errors.append(
                    Issue("unknown_output_path", "出力に存在しない項目を参照しています。", f"{location}/from_path")
                )

    has_review = any((c["kind"], c["implementation"]["ref"]) == HUMAN_REVIEW_KEY for c in contracts.values())
    if not has_review and not workflow["requires_human_approval"]:
        warnings.append(
            Issue("no_human_review", "人の確認も、実行前の承認もない構成です。", "/requires_human_approval")
        )
    return report


def _check_field(
    contracts: dict[str, dict[str, Any]],
    node_id: str,
    field: str,
    source_types: set[str] | None,
    location: str,
    errors: list[Issue],
) -> None:
    contract = contracts.get(node_id)
    if contract is None:
        return
    properties = contract["input_schema"].get("properties", {})
    if field not in properties:
        errors.append(Issue("unknown_input_field", f"ノードに入力 {field} はありません。", location))
        return
    if not _compatible(source_types, _types(properties[field])):
        errors.append(Issue("type_mismatch", f"入力 {field} の型が合いません。", location))
