"""Test-only capabilities (`testkit.*`) for exercising the generic Executor end to end (PHASE2_PLAN §3).

They are registered in the Catalog and bound to code only inside tests: the production allowlist and handler
table never contain them. Functions are module-level so the spawned child process can import them.
"""

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from app.adapters.llm import LlmHandler, MockLlm
from app.adapters.local import LocalHandler
from app.catalog import registry
from app.catalog.registry import ImplementationKey
from app.executor.engine import HandlerTable

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts" / "examples"
FINDING = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rule_id", "severity", "result", "message"],
    "properties": {
        "rule_id": {"type": "string", "pattern": "^[A-Z]{2,8}-[0-9]{3}$"},
        "severity": {"enum": ["critical", "major", "minor"]},
        "result": {"enum": ["pass", "fail", "uncertain"]},
        "message": {"type": "string", "maxLength": 500},
    },
}
DRAFT_OUTPUT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["fields", "findings", "evidence"],
    "properties": {
        "fields": {"type": "object", "maxProperties": 100},
        "findings": {"type": "array", "maxItems": 100, "items": FINDING},
        "evidence": {"type": "object"},
    },
}


# --- implementations (pure functions of inputs and config) ------------------------------------------


def draft(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    text = inputs["text"]
    ok = len(text) >= config.get("min_length", 1)
    return {
        "fields": {"title": text[:50], "length": len(text)},
        "findings": [
            {"rule_id": "TK-001", "severity": "major", "result": "pass" if ok else "fail", "message": "長さの確認"}
        ],
        "evidence": {},
    }


def summarize(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return {"field_count": len(inputs["reviewed_fields"]), "decision": inputs["decision"]}


def sleep_forever(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    while True:
        time.sleep(1)


def raise_error(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    raise ValueError(f"secret input value: {inputs['text']}")


def wrong_shape(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return {"unexpected": True}


def huge_output(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return {"fields": {"blob": "x" * 2_000_000}, "findings": [], "evidence": {}}


def hard_exit(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    os._exit(3)


def flaky(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Fails with an exception on the first call for a given marker file, then succeeds."""
    marker = Path(config["marker"])
    if not marker.exists():
        marker.write_text("1", encoding="utf-8")
        raise RuntimeError("transient")
    return draft(inputs, {"min_length": 1})


# --- contracts --------------------------------------------------------------------------------------


def capability(
    capability_id: str,
    ref: str,
    *,
    kind: str = "local",
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    configuration_schema: dict[str, Any] | None = None,
    timeout_ms: int = 10000,
    retry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "capability_id": capability_id,
        "version": "1.0.0",
        "kind": kind,
        "name": capability_id,
        "description": "試験用（テストの中でだけ登録する）",
        "input_schema": input_schema
        or {
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {"text": {"type": "string", "maxLength": 1000}},
        },
        "output_schema": output_schema or DRAFT_OUTPUT,
        "configuration_schema": configuration_schema
        or {"type": "object", "additionalProperties": False, "properties": {}},
        "implementation": {"ref": ref},
        "tags": ["testkit"],
        "provenance": {"source": "test", "license": "internal_poc", "author": "easf"},
        "timeout_ms": timeout_ms,
        "retry": retry or {"max_attempts": 0, "idempotent": False},
        "side_effects": False,
    }


SUMMARIZE_INPUT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reviewed_fields", "decision"],
    "properties": {
        "reviewed_fields": {"type": "object"},
        "decision": {"enum": ["approved", "approved_with_corrections", "rejected"]},
    },
}
SUMMARIZE_OUTPUT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["field_count", "decision"],
    "properties": {"field_count": {"type": "integer"}, "decision": {"type": "string"}},
}

CONTRACTS: dict[str, dict[str, Any]] = {
    "draft": capability(
        "testkit.draft",
        "testkit.draft.v1",
        configuration_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"min_length": {"type": "integer"}},
        },
        retry={"max_attempts": 1, "idempotent": True},
    ),
    "llm_draft": capability(
        "testkit.llm_draft",
        "testkit.llm_draft.v1",
        kind="llm",
        configuration_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["llm_profile"],
            "properties": {"llm_profile": {"type": "string"}},
        },
    ),
    "summarize": capability(
        "testkit.summarize", "testkit.summarize.v1", input_schema=SUMMARIZE_INPUT, output_schema=SUMMARIZE_OUTPUT
    ),
}

FUNCTIONS = {"testkit.draft.v1": draft, "testkit.summarize.v1": summarize}


def handlers(extra: dict[tuple[str, str], Any] | None = None) -> HandlerTable:
    table: dict[tuple[str, str], Any] = {("local", ref): LocalHandler(f) for ref, f in FUNCTIONS.items()}
    table[("llm", "testkit.llm_draft.v1")] = LlmHandler(MockLlm(draft), instructions="試験用の下書き")
    table.update(extra or {})
    return table


def allow_testkit(monkeypatch: pytest.MonkeyPatch, extra_refs: tuple[tuple[str, str], ...] = ()) -> None:
    """Adds testkit keys to the implementation allowlist for the duration of a test."""
    keys = [("local", r) for r in FUNCTIONS] + [("llm", "testkit.llm_draft.v1"), *extra_refs]
    for kind, ref in keys:
        monkeypatch.setitem(registry.IMPLEMENTATIONS, (kind, ref), ImplementationKey(kind, ref, available=True))


def human_review() -> dict[str, Any]:
    contract: dict[str, Any] = json.loads((EXAMPLES / "capabilities" / "human_review.json").read_text(encoding="utf-8"))
    return contract


def workflow(first: str = "testkit.draft", first_config: dict[str, Any] | None = None, **budget: int) -> dict[str, Any]:
    """text → draft (fields/findings/evidence) → human review → summarize."""
    return {
        "schema_version": "1",
        "workflow_id": "testkit-review",
        "version": 1,
        "name": "試験用の確認フロー",
        "inputs": [{"name": "text", "type": "string", "to": [{"node_id": "draft", "field": "text"}]}],
        "nodes": [
            {
                "node_id": "draft",
                "capability_id": first,
                "capability_version": "1.0.0",
                "config": first_config if first_config is not None else {"min_length": 3},
            },
            {
                "node_id": "review",
                "capability_id": "review.human",
                "capability_version": "1.0.0",
                "config": {"reviewer_role": "business_reviewer", "route_when": "always"},
            },
            {"node_id": "summary", "capability_id": "testkit.summarize", "capability_version": "1.0.0", "config": {}},
        ],
        "edges": [
            {
                "from": "draft",
                "to": "review",
                "mapping": [
                    {"from_path": "/fields", "to_field": "fields"},
                    {"from_path": "/findings", "to_field": "findings"},
                    {"from_path": "/evidence", "to_field": "evidence"},
                ],
            },
            {
                "from": "review",
                "to": "summary",
                "mapping": [
                    {"from_path": "/reviewed_fields", "to_field": "reviewed_fields"},
                    {"from_path": "/decision", "to_field": "decision"},
                ],
            },
        ],
        "outputs": [
            {"name": "field_count", "from_node": "summary", "from_path": "/field_count"},
            {"name": "decision", "from_node": "review", "from_path": "/decision"},
        ],
        "budget": {
            "max_duration_ms": budget.get("max_duration_ms", 60000),
            "max_llm_tokens": budget.get("max_llm_tokens", 100000),
            "max_cost_jpy": budget.get("max_cost_jpy", 0),
        },
        "requires_human_approval": True,
    }


def export_workflow() -> dict[str, Any]:
    """text → draft → human review → result_exporter.v1 (the real exporter; P3-01c)."""
    wf = workflow()
    wf["workflow_id"] = "testkit-export"
    wf["nodes"][2] = {
        "node_id": "export",
        "capability_id": "result.exporter",
        "capability_version": "1.0.0",
        "config": {"format": "csv", "title_ja": "試験の出力"},
    }
    wf["edges"] = [
        wf["edges"][0],
        {
            "from": "review",
            "to": "export",
            "mapping": [
                {"from_path": "/reviewed_fields", "to_field": "reviewed_fields"},
                {"from_path": "/decision", "to_field": "decision"},
            ],
        },
        {"from": "draft", "to": "export", "mapping": [{"from_path": "/findings", "to_field": "findings"}]},
    ]
    wf["outputs"] = [
        {"name": "export_id", "from_node": "export", "from_path": "/export_id"},
        {"name": "decision", "from_node": "review", "from_path": "/decision"},
    ]
    return wf


def exporter_contract() -> dict[str, Any]:
    contract: dict[str, Any] = json.loads(
        (EXAMPLES / "capabilities" / "result_exporter.json").read_text(encoding="utf-8")
    )
    return contract
