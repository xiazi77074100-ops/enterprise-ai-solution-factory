"""P3-01d: the invoice workflow end to end with the production handlers (AC-05, AC-09).

upload → parse → rule-based extract → validate (invoice@1.1.0) → locate evidence (local MCP) → human review →
export. The workflow is configuration (fixtures/workflows/invoice-v2.json); no engine code knows the domain.
"""

import csv
import io
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.db import make_session_factory
from app.executor.handlers import production_handlers
from app.executor.models import NodeRun
from tests.conftest import make_settings
from tests.integration.test_auth_projects import db, migrated  # noqa: F401  # shared fixtures
from tests.integration.test_runs import Env, build_env

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "contracts" / "examples"
WORKFLOW: dict[str, Any] = json.loads((ROOT / "fixtures" / "workflows" / "invoice-v2.json").read_text(encoding="utf-8"))
GOLD: dict[str, Any] = json.loads((ROOT / "fixtures" / "dev" / "labels" / "inv-0001.json").read_text(encoding="utf-8"))


@pytest.fixture
def env(db: Session, db_url: str, monkeypatch: pytest.MonkeyPatch) -> Env:  # noqa: F811
    e = build_env(db, db_url, monkeypatch, production_handlers(make_settings(database_url=db_url)))
    arch, h = e.as_("arch")
    for path in sorted((EXAMPLES / "capabilities").glob("*.json")):
        if path.name == "human_review.json":
            continue  # registered by build_env
        res = arch.post("/api/v1/capabilities", json=json.loads(path.read_text(encoding="utf-8")), headers=h)
        assert res.status_code == 201, (path.name, res.text)
    pack = json.loads((ROOT / "fixtures" / "rule_packs" / "invoice-1.1.0.json").read_text(encoding="utf-8"))
    assert arch.post("/api/v1/rule-packs", json=pack, headers=h).status_code == 201
    return e


def _upload(e: Env, name: str) -> str:
    client, h = e.as_("lead")
    res = client.post(
        f"/api/v1/projects/{e.project_id}/documents",
        files={"file": (name, (ROOT / "fixtures" / "dev" / "documents" / name).read_bytes(), "application/pdf")},
        data={"data_origin": "synthetic"},
        headers=h,
    )
    assert res.status_code == 201, res.text
    document_id: str = res.json()["id"]
    return document_id


def _output(e: Env, run_id: str, node_id: str) -> dict[str, Any]:
    with make_session_factory(make_settings(database_url=e.db_url))() as session:
        node = session.query(NodeRun).filter_by(run_id=uuid.UUID(run_id), node_id=node_id).one()
        assert node.output is not None
        return dict(node.output)


def _run_to_review(e: Env, sid: str, document_id: str) -> tuple[str, dict[str, Any]]:
    started = e.start(sid, {"document": document_id})
    assert started.status_code == 202, started.text
    run_id: str = started.json()["id"]
    e.executor().run_until_idle()
    run = e.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "waiting_review", (run, e.get(f"/api/v1/runs/{run_id}/nodes"))
    return run_id, e.review_of(run_id)


def _approve(e: Env, run_id: str, task: dict[str, Any]) -> None:
    who = next(name for name, uid in e.users.items() if uid == task["assigned_to"])
    assert e.decide(run_id, task["id"], {"decision": "approved"}, who=who).status_code == 200
    e.executor().run_until_idle()


def test_invoice_workflow_end_to_end(env: Env) -> None:
    sid = env.solution(WORKFLOW)
    document_id = _upload(env, "inv-0001.pdf")
    run_id, task = _run_to_review(env, sid, document_id)

    # Every node ran for real (local code and the local MCP server; nothing mocked).
    nodes = env.get(f"/api/v1/runs/{run_id}/nodes")
    assert {n["execution_mode"] for n in nodes} == {"real"}
    extract = _output(env, run_id, "extract")
    assert extract["fields"]["invoice_no"] == GOLD["gold_fields"]["invoice_no"]
    locate = _output(env, run_id, "locate")
    span = locate["evidence"]["invoice_no"][0]
    assert span["status"] == "verified" and span["document_id"] == document_id
    assert {k: span[k] for k in ("page", "start", "end", "text_sha256")} == GOLD["gold_evidence"]["invoice_no"][0]
    # The review task carries the AI draft, the rule findings and the evidence for the reviewer.
    assert task["items"], task

    _approve(env, run_id, task)
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "succeeded" and run["execution_mode"] == "real"

    client, _ = env.as_("lead")
    exported = client.get(f"/api/v1/runs/{run_id}/export?format=csv")
    assert exported.status_code == 200
    rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert rows[0] == ["請求書の確認結果"]
    assert ["項目", "invoice_no", GOLD["gold_fields"]["invoice_no"], "", ""] in rows


def test_second_run_on_the_same_invoice_is_flagged_as_duplicate(env: Env) -> None:
    """AC-09: a duplicate is not passed silently. INV-006 reads the project context of earlier runs."""
    sid = env.solution(WORKFLOW)
    first_id, first_task = _run_to_review(env, sid, _upload(env, "inv-0001.pdf"))
    first = {f["rule_id"]: f["result"] for f in _output(env, first_id, "validate")["findings"]}
    assert first["INV-006"] == "pass"
    _approve(env, first_id, first_task)

    second_id, _ = _run_to_review(env, sid, _upload(env, "inv-0001.pdf"))
    second = _output(env, second_id, "validate")
    assert {f["rule_id"]: f["result"] for f in second["findings"]}["INV-006"] == "fail"
    assert second["requires_review"] is True
