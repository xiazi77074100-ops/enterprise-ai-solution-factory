"""Composer (run_execution.md §2): the frozen example workflows pass; each kind of mistake is reported."""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.composer.validation import resolve_pointer, validate_workflow

EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"
CONTRACTS = {
    (c["capability_id"], c["version"]): c
    for c in (json.loads(p.read_text(encoding="utf-8")) for p in (EXAMPLES / "capabilities").glob("*.json"))
}


def lookup(capability_id: str, version: str) -> dict[str, Any] | None:
    return CONTRACTS.get((capability_id, version))


def example(name: str) -> dict[str, Any]:
    workflow: dict[str, Any] = json.loads((EXAMPLES / "workflows" / f"{name}.json").read_text(encoding="utf-8"))
    return workflow


def codes(workflow: dict[str, Any]) -> set[str]:
    return {i.code for i in validate_workflow(workflow, lookup).errors}


@pytest.mark.parametrize("name", ["invoice", "contract"])
def test_example_workflows_are_valid(name: str) -> None:
    report = validate_workflow(example(name), lookup)
    assert report.errors == []
    # Every example capability has code bound since P3-01c: no implementation_unavailable warning.
    assert report.warnings == []


def _node(w: dict[str, Any], node_id: str) -> dict[str, Any]:
    node: dict[str, Any] = next(n for n in w["nodes"] if n["node_id"] == node_id)
    return node


def _edge(w: dict[str, Any], src: str, dst: str) -> dict[str, Any]:
    edge: dict[str, Any] = next(e for e in w["edges"] if e["from"] == src and e["to"] == dst)
    return edge


def _new_edge(src: str, dst: str, from_path: str, to_field: str) -> dict[str, Any]:
    return {"from": src, "to": dst, "mapping": [{"from_path": from_path, "to_field": to_field}]}


MUTATIONS: dict[str, tuple[Callable[[dict[str, Any]], None], str]] = {
    "schema": (lambda w: w.pop("budget"), "schema_violation"),
    "duplicate node": (lambda w: w["nodes"].append(copy.deepcopy(w["nodes"][0])), "duplicate_node"),
    "unregistered version": (
        lambda w: _node(w, "parse").update(capability_version="9.9.9"),
        "unknown_capability_version",
    ),
    "config violates schema": (lambda w: _node(w, "parse").update(config={"ocr": "magic"}), "config_schema"),
    "timeout above capability": (lambda w: _node(w, "parse").update(timeout_ms=120000), "timeout_exceeds_capability"),
    "cycle": (
        lambda w: w["edges"].append(_new_edge("export", "parse", "/format", "document_ref")),
        "cycle",
    ),
    "edge to unknown node": (lambda w: _edge(w, "parse", "extract").update(to="ghost"), "unknown_node"),
    "output path does not exist": (
        lambda w: _edge(w, "parse", "extract")["mapping"][0].update(from_path="/nope"),
        "unknown_output_path",
    ),
    "input field does not exist": (
        lambda w: _edge(w, "parse", "extract")["mapping"][0].update(to_field="nope"),
        "unknown_input_field",
    ),
    "type mismatch (array into string)": (
        lambda w: _edge(w, "parse", "extract")["mapping"][0].update(from_path="/pages"),
        "type_mismatch",
    ),
    "workflow input type mismatch": (lambda w: w["inputs"][0].update(type="integer"), "type_mismatch"),
    "missing required input": (lambda w: w["edges"].remove(_edge(w, "validate", "review")), "missing_input"),
    "same field fed twice": (
        lambda w: w["edges"].append(_new_edge("parse", "export", "/document_id", "decision")),
        "duplicate_input",
    ),
    "workflow output path does not exist": (lambda w: w["outputs"][0].update(from_path="/nope"), "unknown_output_path"),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(MUTATIONS))
def test_mistakes_are_reported(case: str) -> None:
    mutate, expected = MUTATIONS[case]
    workflow = example("invoice")
    mutate(workflow)
    assert expected in codes(workflow)


def test_unreachable_node_is_reported() -> None:
    workflow = example("invoice")
    extra = copy.deepcopy(_node(workflow, "parse")) | {"node_id": "orphan"}
    workflow["nodes"].append(extra)
    assert codes(workflow) == {"unreachable_node", "missing_input"}


def test_no_review_and_no_approval_is_a_warning() -> None:
    workflow = example("invoice")
    workflow["requires_human_approval"] = False
    workflow["nodes"] = [_node(workflow, "parse")]
    workflow["edges"] = []
    workflow["outputs"] = [{"name": "doc", "from_node": "parse", "from_path": "/document_id"}]
    report = validate_workflow(workflow, lookup)
    assert report.errors == []
    assert "no_human_review" in {w.code for w in report.warnings}


def test_resolve_pointer() -> None:
    schema = {
        "type": "object",
        "properties": {
            "pages": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}}}},
            "fields": {"type": "object", "additionalProperties": {"type": "integer"}},
        },
    }
    assert resolve_pointer(schema, "/pages/0/text") == {"type": "string"}
    assert resolve_pointer(schema, "/fields/total") == {"type": "integer"}
    assert resolve_pointer(schema, "/missing") is None
    assert resolve_pointer(schema, "/pages/x") is None
