"""P3-01b capabilities through the real handlers and the Executor: upload → parse → extract → validate."""

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.adapters.resources import RulePackHandler, StoredDocumentHandler
from app.capabilities.document_parser import parse_document
from app.capabilities.rule_validator import validate_rules
from app.core.db import make_session_factory
from app.executor.handlers import production_handlers
from tests.conftest import STORAGE_DIR, make_settings
from tests.integration.test_auth_projects import db, migrated  # noqa: F401  # shared fixtures
from tests.integration.test_runs import Env, build_env

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "contracts" / "examples"
DEV = ROOT / "fixtures" / "dev"

# Labels printed on the synthetic invoices (fixtures/generator/render.py); configuration, not code.
FIELD_SPEC = [
    {"name": "invoice_no", "type": "string", "label_ja": "請求書番号", "critical": True, "labels": ["請求書番号"]},
    {"name": "issue_date", "type": "date", "label_ja": "請求日", "critical": False, "labels": ["請求日"]},
    {"name": "total", "type": "decimal", "label_ja": "合計", "critical": True, "labels": ["合計金額", "ご請求金額"]},
]


def _workflow(extractor: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    capability_id, config = extractor
    return {
        "schema_version": "1",
        "workflow_id": "doc-capabilities",
        "version": 1,
        "name": "文書の解析・抽出・検証",
        "inputs": [{"name": "document", "type": "document_ref", "to": [{"node_id": "parse", "field": "document_ref"}]}],
        "nodes": [
            {"node_id": "parse", "capability_id": "document.parser", "capability_version": "1.0.0",
             "config": {"ocr": "none"}},
            {"node_id": "extract", "capability_id": capability_id, "capability_version": "1.0.0", "config": config},
            {"node_id": "validate", "capability_id": "document.rule_validator", "capability_version": "1.0.0",
             "config": {"rule_pack_id": "invoice", "rule_pack_version": "1.1.0"}},
        ],
        "edges": [
            {"from": "parse", "to": "extract", "mapping": [{"from_path": "/document_id", "to_field": "document_id"},
                                                           {"from_path": "/pages", "to_field": "pages"}]},
            {"from": "extract", "to": "validate", "mapping": [{"from_path": "/fields", "to_field": "fields"},
                                                              {"from_path": "/field_status",
                                                               "to_field": "field_status"}]},
        ],
        "outputs": [{"name": "findings", "from_node": "validate", "from_path": "/findings"}],
        "budget": {"max_duration_ms": 300000, "max_llm_tokens": 100000, "max_cost_jpy": 0},
        "requires_human_approval": False,
    }  # fmt: skip


RULE_EXTRACTOR = ("document.rule_extractor", {"field_spec": FIELD_SPEC})
LLM_EXTRACTOR = (
    "document.extractor",
    {
        "llm_profile": "extractor_default",
        "field_spec": [{k: v for k, v in f.items() if k != "labels"} for f in FIELD_SPEC],
    },
)


@pytest.fixture
def env(db: Session, db_url: str, monkeypatch: pytest.MonkeyPatch) -> Env:  # noqa: F811
    settings = make_settings(database_url=db_url)
    e = build_env(db, db_url, monkeypatch, production_handlers(settings))
    arch, h = e.as_("arch")
    for name in ("document_parser", "rule_based_extractor", "structured_extractor", "rule_validator"):
        contract = json.loads((EXAMPLES / "capabilities" / f"{name}.json").read_text(encoding="utf-8"))
        assert arch.post("/api/v1/capabilities", json=contract, headers=h).status_code == 201
    pack = json.loads((ROOT / "fixtures" / "rule_packs" / "invoice-1.1.0.json").read_text(encoding="utf-8"))
    assert arch.post("/api/v1/rule-packs", json=pack, headers=h).status_code == 201
    return e


def _upload(e: Env, name: str) -> str:
    client, h = e.as_("lead")
    data = (DEV / "documents" / name).read_bytes()
    media = "application/pdf" if name.endswith(".pdf") else "image/png"
    res = client.post(
        f"/api/v1/projects/{e.project_id}/documents",
        files={"file": (name, data, media)},
        data={"data_origin": "synthetic"},
        headers=h,
    )
    assert res.status_code == 201, res.text
    document_id: str = res.json()["id"]
    return document_id


def _run(e: Env, workflow: dict[str, Any], document_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sid = e.solution(workflow, approve=False)
    started = e.start(sid, {"document": document_id})
    assert started.status_code == 202, started.text
    e.executor().run_until_idle()
    run = e.get(f"/api/v1/runs/{started.json()['id']}")
    nodes = {n["node_id"]: n for n in e.get(f"/api/v1/runs/{run['id']}/nodes")}
    return run, nodes


def test_rule_based_pipeline_runs_for_real(env: Env) -> None:
    gold = json.loads((DEV / "labels" / "inv-0001.json").read_text(encoding="utf-8"))
    run, nodes = _run(env, _workflow(RULE_EXTRACTOR), _upload(env, "inv-0001.pdf"))
    assert run["status"] == "succeeded", (run, nodes)
    assert run["execution_mode"] == "real"
    assert all(n["execution_mode"] == "real" for n in nodes.values())
    # Node outputs are stored but the API exposes summaries only; compare via the trace-free DB row.
    from app.executor.models import NodeRun  # noqa: PLC0415

    with make_session_factory(make_settings(database_url=env.db_url))() as session:
        extract = session.get(NodeRun, uuid.UUID(nodes["extract"]["id"]))
        assert extract is not None and extract.output is not None
        assert extract.output["fields"]["invoice_no"] == gold["gold_fields"]["invoice_no"]
        assert extract.output["field_status"]["invoice_no"] == "found"
        validate = session.get(NodeRun, uuid.UUID(nodes["validate"]["id"]))
        assert validate is not None and validate.output is not None
        results = {f["rule_id"]: f["result"] for f in validate.output["findings"]}
    # Only three fields are configured here, so rules on the other fields see missing values.
    assert results["INV-002"] == "fail"  # registration_no not extracted -> on_missing: fail
    assert results["INV-004"] == "uncertain"
    assert results["INV-006"] == "pass"  # first run of the project: the context is empty


def test_llm_extractor_is_mock_and_marks_the_run_mixed(env: Env) -> None:
    run, nodes = _run(env, _workflow(LLM_EXTRACTOR), _upload(env, "inv-0001.pdf"))
    assert run["status"] == "succeeded", (run, nodes)
    assert nodes["extract"]["execution_mode"] == "mock"
    assert run["execution_mode"] == "mixed"  # never counted as real extraction


def test_image_without_ocr_still_runs_and_reports_missing(env: Env) -> None:
    run, nodes = _run(env, _workflow(RULE_EXTRACTOR), _upload(env, "inv-0008.png"))
    assert run["status"] == "succeeded", (run, nodes)
    assert nodes["parse"]["output_summary"] is not None


def test_unresolvable_references_fail_without_retry(env: Env) -> None:
    factory = make_session_factory(make_settings(database_url=env.db_url))
    missing = StoredDocumentHandler(parse_document, factory, Path(STORAGE_DIR)).invoke(
        {"document_ref": str(uuid.uuid4())}, {"ocr": "none"}, 10
    )
    assert (missing.status, missing.error_code) == ("unavailable", "document_not_found")
    no_pack = RulePackHandler(validate_rules, factory).invoke(
        {"fields": {}, "field_status": {}}, {"rule_pack_id": "nothing", "rule_pack_version": "1.0.0"}, 10
    )
    assert (no_pack.status, no_pack.error_code) == ("unavailable", "rule_pack_not_found")
