"""P3-01c end to end: the MCP adapter over real stdio, and exportRunResult on a reviewed run."""

import csv
import io
import uuid
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.adapters.local import LocalHandler
from app.adapters.mcp import McpToolHandler
from app.capabilities.result_exporter import export_result
from app.core.db import make_session_factory
from app.executor.models import NodeRun
from tests import executor_testkit as kit
from tests.conftest import make_settings
from tests.integration.test_auth_projects import db, migrated  # noqa: F401  # shared fixtures
from tests.integration.test_runs import Env, build_env

DOC = "00000000-0000-0000-0000-000000000001"
TEXT = "請求書番号：2025-0001\r\n合計金額：¥104,060\r\n"
PAGES = [{"page": 1, "text": TEXT, "extraction_method": "text_layer"}]


def test_mcp_adapter_calls_the_local_server_over_stdio() -> None:
    handler = McpToolHandler("locate_evidence")
    ok = handler.invoke(
        {"document_id": DOC, "pages": PAGES, "fields": {"total": "104060"}}, {"match": "normalized"}, 60
    )
    assert ok.status == "ok" and ok.execution_mode == "real"
    assert ok.output is not None and ok.output["evidence"]["total"][0]["start"] == TEXT.index("¥104,060")
    bad_input = handler.invoke({"document_id": DOC, "pages": PAGES, "fields": {}}, {"match": "fuzzy"}, 60)
    assert (bad_input.status, bad_input.error_code) == ("error", "mcp_tool_error")
    not_advertised = McpToolHandler("run_shell").invoke({}, {}, 60)
    assert (not_advertised.status, not_advertised.error_code) == ("unavailable", "mcp_tool_not_advertised")
    too_slow = handler.invoke({"document_id": DOC, "pages": PAGES, "fields": {}}, {"match": "exact"}, 0.01)
    assert too_slow.status == "timeout"


@pytest.fixture
def env(db: Session, db_url: str, monkeypatch: pytest.MonkeyPatch) -> Env:  # noqa: F811
    e = build_env(db, db_url, monkeypatch, kit.handlers({("local", "result_exporter.v1"): LocalHandler(export_result)}))
    arch, h = e.as_("arch")
    assert arch.post("/api/v1/capabilities", json=kit.exporter_contract(), headers=h).status_code == 201
    return e


def _reviewed_run(e: Env, decision: dict[str, Any]) -> str:
    sid = e.solution(kit.export_workflow())
    run_id: str = e.start(sid, {"text": "出力の試験"}).json()["id"]
    e.executor().run_until_idle()
    task = e.review_of(run_id)
    assert e.decide(run_id, task["id"], decision, who=_assignee(e, task)).status_code == 200
    e.executor().run_until_idle()
    return run_id


def _assignee(e: Env, task: dict[str, Any]) -> str:
    return next(name for name, uid in e.users.items() if uid == task["assigned_to"])


@pytest.mark.db
def test_export_csv_and_json_of_a_reviewed_run(env: Env) -> None:
    correction = {"path": "/fields/title", "corrected_value": '=HYPERLINK("http://example.invalid")'}
    run_id = _reviewed_run(env, {"decision": "approved_with_corrections", "corrections": [correction]})
    assert env.get(f"/api/v1/runs/{run_id}")["status"] == "succeeded"
    client, _ = env.as_("lead")

    res = client.get(f"/api/v1/runs/{run_id}/export?format=csv")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/csv")
    assert res.headers["content-disposition"] == f'attachment; filename="run-{run_id}.csv"'
    assert res.headers["cache-control"] == "no-store" and res.headers["x-content-type-options"] == "nosniff"
    assert res.content.startswith("﻿".encode())
    rows = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig"))))
    assert rows[0] == ["試験の出力"]
    assert ["項目", "title", '\'=HYPERLINK("http://example.invalid")', "", ""] in rows  # CSV injection neutralized
    assert ["判定", "decision", "修正して承認", "", ""] in rows

    exported = client.get(f"/api/v1/runs/{run_id}/export?format=json")
    assert exported.status_code == 200
    body = exported.json()
    assert body["run_id"] == run_id and body["decision"] == "approved_with_corrections"
    assert body["fields"]["title"].startswith("=")  # JSON keeps the value as data

    reviewer, _ = env.as_("reviewer")
    assert reviewer.get(f"/api/v1/runs/{run_id}/export?format=csv").status_code == 200
    arch, _ = env.as_("arch")
    assert arch.get(f"/api/v1/runs/{run_id}/export?format=csv").status_code == 403
    outsider, _ = env.as_("outsider")
    assert outsider.get(f"/api/v1/runs/{run_id}/export?format=csv").status_code == 404
    assert client.get(f"/api/v1/runs/{run_id}/export?format=xlsx").status_code == 422


@pytest.mark.db
def test_only_succeeded_runs_with_an_exporter_can_be_exported(env: Env) -> None:
    rejected = _reviewed_run(env, {"decision": "rejected", "comment": "誤り"})
    client, _ = env.as_("lead")
    res = client.get(f"/api/v1/runs/{rejected}/export?format=csv")
    assert res.status_code == 409 and res.json()["code"] == "run_not_exportable"
    waiting = env.start(env.solution(kit.export_workflow()), {"text": "確認待ち"}).json()["id"]
    env.executor().run_until_idle()
    assert client.get(f"/api/v1/runs/{waiting}/export?format=json").status_code == 409


@pytest.mark.db
def test_tampered_node_output_is_not_exported(env: Env) -> None:
    run_id = _reviewed_run(env, {"decision": "approved"})
    with make_session_factory(make_settings(database_url=env.db_url))() as session:
        session.execute(
            update(NodeRun)
            .where(NodeRun.run_id == uuid.UUID(run_id), NodeRun.node_id == "review")
            .values(output={"reviewed_fields": {"title": "差し替え"}, "decision": "approved", "corrections": []})
        )
        session.commit()
    client, _ = env.as_("lead")
    res = client.get(f"/api/v1/runs/{run_id}/export?format=csv")
    assert res.status_code == 409 and res.json()["code"] == "export_mismatch"
