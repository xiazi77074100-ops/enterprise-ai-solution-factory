"""Executor end to end (PHASE2_PLAN §3, run_execution.md §3〜§7) with test-only capabilities and the real
human review: start → worker → pause for review → decide → resume → succeeded / rejected, plus the trace."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import make_session_factory
from app.executor.engine import Executor, HandlerTable
from app.executor.events import verify_chain
from app.main import create_app
from tests import executor_testkit as kit
from tests.conftest import make_settings
from tests.integration.test_auth_projects import (  # noqa: F401  # shared fixtures
    ORIGIN,
    PASSWORD,
    db,
    make_user,
    migrated,
)

pytestmark = pytest.mark.db


@dataclass
class Env:
    db_url: str
    handlers: HandlerTable
    project_id: str
    requirement_id: str
    users: dict[str, str]
    sessions: dict[str, tuple[TestClient, dict[str, str]]]

    def as_(self, name: str) -> tuple[TestClient, dict[str, str]]:
        return self.sessions[name]

    def executor(self) -> Executor:
        return Executor(make_session_factory(make_settings(database_url=self.db_url)), self.handlers)

    def solution(self, workflow: dict[str, Any], approve: bool = True) -> str:
        arch, h = self.as_("arch")
        body = {"project_id": self.project_id, "requirement_revision_id": self.requirement_id, "workflow": workflow}
        created = arch.post("/api/v1/solutions", json=body, headers=h)
        assert created.status_code == 201, created.text
        sid: str = created.json()["id"]
        report = arch.post(f"/api/v1/solutions/{sid}/validate", headers=h).json()
        assert report["valid"], report
        if approve:
            lead, lh = self.as_("lead")
            assert lead.post(f"/api/v1/solutions/{sid}/approve", headers=lh).status_code == 200
        return sid

    def start(self, sid: str, inputs: dict[str, Any], key: str | None = None, who: str = "lead") -> Any:
        client, h = self.as_(who)
        return client.post(
            f"/api/v1/solutions/{sid}/runs",
            json={"inputs": inputs},
            headers={**h, "Idempotency-Key": key or str(uuid.uuid4())},
        )

    def get(self, path: str, who: str = "lead") -> Any:
        client, _ = self.as_(who)
        res = client.get(path)
        assert res.status_code == 200, res.text
        return res.json()

    def decide(
        self, run_id: str, review_id: str, body: dict[str, Any], who: str = "reviewer", key: str | None = None
    ) -> Any:
        client, h = self.as_(who)
        return client.post(
            f"/api/v1/runs/{run_id}/reviews/{review_id}/decision",
            json=body,
            headers={**h, "Idempotency-Key": key or str(uuid.uuid4())},
        )

    def review_of(self, run_id: str) -> dict[str, Any]:
        # Either reviewer may be assigned (load balancing): look through the lead's view of the project.
        tasks = self.get("/api/v1/reviews?status=pending&assigned_to_me=false", who="lead")["items"]
        task: dict[str, Any] = next(t for t in tasks if t["run_id"] == run_id)
        return task


def build_env(
    session: Session, db_url: str, monkeypatch: pytest.MonkeyPatch, handlers: HandlerTable, reviewers: bool = True
) -> Env:
    kit.allow_testkit(monkeypatch)
    names = ("lead", "arch", "reviewer", "reviewer2", "qa", "outsider")
    users = {n: str(make_user(session, n).id) for n in names}
    admin = make_user(session, "admin", admin=True)

    def login(name: str) -> tuple[TestClient, dict[str, str]]:
        client = TestClient(
            create_app(make_settings(database_url=db_url), handlers=handlers), raise_server_exceptions=False
        )
        res = client.post("/api/v1/session", json={"login_id": name, "password": PASSWORD}, headers=ORIGIN)
        assert res.status_code == 200, res.text
        return client, {**ORIGIN, "X-CSRF-Token": res.json()["csrf_token"]}

    sessions = {n: login(n) for n in (*names, "admin")}
    a, ah = sessions["admin"]
    project = a.post("/api/v1/projects", json={"name": "試験", "business_domain": "試験"}, headers=ah).json()["id"]
    members = [
        {"user_id": str(admin.id), "roles": ["solution_lead"]},
        {"user_id": users["lead"], "roles": ["solution_lead"]},
        {"user_id": users["arch"], "roles": ["solution_architect"]},
        {"user_id": users["qa"], "roles": ["qa_evaluator"]},
    ]
    if reviewers:
        members += [
            {"user_id": users["reviewer"], "roles": ["business_reviewer"]},
            {"user_id": users["reviewer2"], "roles": ["business_reviewer"]},
        ]
    assert a.put(f"/api/v1/projects/{project}/members", json=members, headers=ah).status_code == 200
    arch, h = sessions["arch"]
    for contract in [*kit.CONTRACTS.values(), kit.human_review()]:
        assert arch.post("/api/v1/capabilities", json=contract, headers=h).status_code == 201
    requirement = arch.post(f"/api/v1/projects/{project}/requirements", json={"content": "要件"}, headers=h).json()[
        "id"
    ]
    assert a.post(f"/api/v1/requirements/{requirement}/approve", headers=ah).status_code == 200
    return Env(db_url, handlers, project, requirement, users, sessions)


@pytest.fixture
def env_factory(db: Session, db_url: str, monkeypatch: pytest.MonkeyPatch) -> Callable[..., Env]:  # noqa: F811
    def make(handlers: HandlerTable | None = None, reviewers: bool = True) -> Env:
        return build_env(db, db_url, monkeypatch, kit.handlers() if handlers is None else handlers, reviewers)

    return make


@pytest.fixture
def env(env_factory: Callable[..., Env]) -> Env:
    return env_factory()


def event_types(env: Env, run_id: str) -> list[str]:
    return [e["event_type"] for e in env.get(f"/api/v1/runs/{run_id}/trace?limit=200")["items"]]


def test_run_pauses_for_review_and_succeeds_with_corrections(env: Env, migration_url: str) -> None:
    sid = env.solution(kit.workflow())
    started = env.start(sid, {"text": "試験の文書"})
    assert started.status_code == 202, started.text
    run_id = started.json()["id"]
    assert started.json()["status"] == "pending"

    assert env.executor().run_until_idle() == 1
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "waiting_review" and run["execution_mode"] == "real"
    nodes = {n["node_id"]: n for n in env.get(f"/api/v1/runs/{run_id}/nodes")}
    assert [nodes[n]["status"] for n in ("draft", "review", "summary")] == ["succeeded", "waiting_review", "pending"]
    assert nodes["draft"]["output_summary"] == {"fields": 2, "findings": 1, "evidence": 0}

    task = env.review_of(run_id)
    assert task["assigned_to"] in (env.users["reviewer"], env.users["reviewer2"])
    reviewer = "reviewer" if task["assigned_to"] == env.users["reviewer"] else "reviewer2"
    paths = {i["path"]: i for i in task["items"]}
    assert paths["/fields/title"]["proposed_value"] == "試験の文書" and paths["/fields/title"]["origin"] == "parser"
    assert paths["/findings/0"]["flags"] == [{"rule_id": "TK-001", "severity": "major", "result": "pass"}]

    decided = env.decide(
        run_id,
        task["id"],
        {
            "decision": "approved_with_corrections",
            "corrections": [{"path": "/fields/title", "corrected_value": "修正後"}],
        },
        who=reviewer,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "completed" and decided.json()["decided_by"] == env.users[reviewer]
    assert env.get(f"/api/v1/runs/{run_id}")["status"] == "running"

    env.executor().run_until_idle()
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "succeeded" and run["failure_code"] is None and run["finished_at"]
    assert {n["status"] for n in env.get(f"/api/v1/runs/{run_id}/nodes")} == {"succeeded"}

    assert event_types(env, run_id) == [
        "run.started", "node.started", "node.completed", "review.requested",
        "review.completed", "node.completed", "node.started", "node.completed", "run.completed",
    ]  # fmt: skip
    trace = env.get(f"/api/v1/runs/{run_id}/trace?limit=200")["items"]
    review_done = next(e for e in trace if e["event_type"] == "review.completed")
    assert review_done["actor"] == {"type": "user", "id": env.users[reviewer]}
    assert review_done["redacted_metadata"]["corrected_paths"] == "/fields/title"
    assert "修正後" not in str(trace) and "試験の文書" not in str(trace)  # values never reach the trace

    with Session(create_engine(migration_url)) as s:
        assert verify_chain(s, uuid.UUID(run_id))
        reviewed = s.execute(
            text("SELECT output FROM node_run WHERE run_id = :r AND node_id = 'review'"), {"r": run_id}
        ).scalar_one()
        assert reviewed["reviewed_fields"]["title"] == "修正後" and reviewed["decision"] == "approved_with_corrections"
        outputs = s.execute(text("SELECT outputs FROM run WHERE id = :r"), {"r": run_id}).scalar_one()
        assert outputs == {"field_count": 2, "decision": "approved_with_corrections"}


def test_rejected_review_stops_the_run(env: Env) -> None:
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "却下する文書"}).json()["id"]
    env.executor().run_until_idle()
    task = env.review_of(run_id)
    who = "reviewer" if task["assigned_to"] == env.users["reviewer"] else "reviewer2"
    assert env.decide(run_id, task["id"], {"decision": "rejected"}, who=who).status_code == 422  # comment required
    assert env.decide(run_id, task["id"], {"decision": "rejected", "comment": "根拠不足"}, who=who).status_code == 200
    env.executor().run_until_idle()
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "rejected"
    nodes = {n["node_id"]: n for n in env.get(f"/api/v1/runs/{run_id}/nodes")}
    assert nodes["review"]["status"] == "failed" and nodes["review"]["error_code"] == "rejected"
    assert nodes["summary"]["status"] == "skipped"
    assert event_types(env, run_id)[-1] == "run.completed"


def test_same_input_reproduces_hashes_and_trace(env: Env) -> None:
    sid = env.solution(kit.workflow())

    def run_once() -> tuple[str, list[tuple[str, Any, Any]], list[str]]:
        run_id = env.start(sid, {"text": "同じ入力"}).json()["id"]
        env.executor().run_until_idle()
        task = env.review_of(run_id)
        who = "reviewer" if task["assigned_to"] == env.users["reviewer"] else "reviewer2"
        env.decide(run_id, task["id"], {"decision": "approved"}, who=who)
        env.executor().run_until_idle()
        run = env.get(f"/api/v1/runs/{run_id}")
        assert run["status"] == "succeeded"
        nodes = [(n["node_id"], n["input_sha256"], n["output_sha256"]) for n in env.get(f"/api/v1/runs/{run_id}/nodes")]
        return run["input_sha256"], nodes, event_types(env, run_id)

    first, second = run_once(), run_once()
    assert first == second


def test_mock_llm_node_marks_the_run_mixed(env: Env) -> None:
    sid = env.solution(kit.workflow("testkit.llm_draft", {"llm_profile": "test_default"}))
    run_id = env.start(sid, {"text": "模擬の LLM"}).json()["id"]
    env.executor().run_until_idle()
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["execution_mode"] == "mixed"  # mock LLM + real human review
    assert run["usage"]["llm_input_tokens"] > 0 and run["usage"]["cost_jpy"] == 0 and run["usage"]["cost_known"]
    draft = next(n for n in env.get(f"/api/v1/runs/{run_id}/nodes") if n["node_id"] == "draft")
    assert draft["execution_mode"] == "mock" and draft["llm"]["provider"] == "mock"
    task = env.review_of(run_id)
    assert {i["origin"] for i in task["items"] if i["path"].startswith("/fields/")} == {"ai_draft"}


def test_llm_token_budget_fails_the_run(env: Env) -> None:
    sid = env.solution(kit.workflow("testkit.llm_draft", {"llm_profile": "test_default"}, max_llm_tokens=1))
    run_id = env.start(sid, {"text": "予算を超える"}).json()["id"]
    env.executor().run_until_idle()
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "failed" and run["failure_code"] == "budget_exceeded"
    statuses = {n["node_id"]: n["status"] for n in env.get(f"/api/v1/runs/{run_id}/nodes")}
    assert statuses == {"draft": "failed", "review": "skipped", "summary": "skipped"}


def test_idempotency_key(env: Env) -> None:
    sid = env.solution(kit.workflow())
    key = str(uuid.uuid4())
    first = env.start(sid, {"text": "一回目"}, key=key)
    again = env.start(sid, {"text": "一回目"}, key=key)
    assert first.status_code == again.status_code == 202 and first.json()["id"] == again.json()["id"]
    conflict = env.start(sid, {"text": "別の内容"}, key=key)
    assert conflict.status_code == 409 and conflict.json()["code"] == "idempotency_conflict"
    assert env.get(f"/api/v1/runs?project_id={env.project_id}")["page"]["total"] == 1


def test_start_preconditions(env: Env) -> None:
    unapproved = env.solution(kit.workflow(), approve=False)
    res = env.start(unapproved, {"text": "x"})
    assert res.status_code == 409 and res.json()["code"] == "solution_not_runnable"

    sid = env.solution(kit.workflow())
    for inputs in ({}, {"text": 1}, {"text": "x", "extra": "y"}):
        assert env.start(sid, inputs).status_code == 422, inputs
    assert env.start(sid, {"text": "x"}, who="reviewer").status_code == 403
    assert env.start(sid, {"text": "x"}, who="outsider").status_code == 404
    assert env.start(sid, {"text": "x"}, who="qa").status_code == 202


def test_capability_without_code_cannot_start(env_factory: Callable[..., Env]) -> None:
    env = env_factory(handlers={})  # the allowlist knows testkit keys, but no code is bound in this table
    sid = env.solution(kit.workflow())
    res = env.start(sid, {"text": "x"})
    assert res.status_code == 409 and res.json()["code"] == "implementation_unavailable"


def test_review_decision_rules(env: Env) -> None:
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "決定の規則"}).json()["id"]
    env.executor().run_until_idle()
    task = env.review_of(run_id)
    assignee = "reviewer" if task["assigned_to"] == env.users["reviewer"] else "reviewer2"
    other = "reviewer2" if assignee == "reviewer" else "reviewer"
    url = f"/api/v1/runs/{run_id}/reviews/{task['id']}"

    assert env.decide(run_id, task["id"], {"decision": "approved"}, who=other).status_code == 403  # not assigned
    assert env.decide(run_id, task["id"], {"decision": "approved"}, who="lead").status_code == 403  # no role
    assert env.decide(run_id, task["id"], {"decision": "approved"}, who="outsider").status_code == 404
    bad_path = {
        "decision": "approved_with_corrections",
        "corrections": [{"path": "/findings/0", "corrected_value": "x"}],
    }
    assert env.decide(run_id, task["id"], bad_path, who=assignee).json()["code"] == "invalid_correction_path"
    no_corrections = {"decision": "approved_with_corrections", "corrections": []}
    assert env.decide(run_id, task["id"], no_corrections, who=assignee).status_code == 422

    key = str(uuid.uuid4())
    first = env.decide(run_id, task["id"], {"decision": "approved"}, who=assignee, key=key)
    assert first.status_code == 200
    replay = env.decide(run_id, task["id"], {"decision": "approved"}, who=assignee, key=key)
    assert replay.status_code == 200 and replay.json() == first.json()
    twice = env.decide(run_id, task["id"], {"decision": "rejected", "comment": "x"}, who=assignee)
    assert twice.status_code == 409 and twice.json()["code"] == "already_decided"
    assert env.get(url, who="qa")["decision"] == "approved"  # any member can read it


def test_reviews_are_balanced_between_reviewers(env: Env) -> None:
    sid = env.solution(kit.workflow())
    runs = [env.start(sid, {"text": f"文書{i}"}).json()["id"] for i in range(2)]
    env.executor().run_until_idle()
    tasks = env.get("/api/v1/reviews?assigned_to_me=false", who="lead")["items"]
    assignees = {t["assigned_to"] for t in tasks if t["run_id"] in runs}
    assert assignees == {env.users["reviewer"], env.users["reviewer2"]}


def test_no_reviewer_fails_the_run(env_factory: Callable[..., Env]) -> None:
    env = env_factory(reviewers=False)
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "確認者なし"}).json()["id"]
    env.executor().run_until_idle()
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "failed" and run["failure_code"] == "no_reviewer"


def test_isolation_and_review_list_permissions(env: Env) -> None:
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "分離"}).json()["id"]
    env.executor().run_until_idle()
    outsider, _ = env.as_("outsider")
    for path in (f"/api/v1/runs/{run_id}", f"/api/v1/runs/{run_id}/nodes", f"/api/v1/runs/{run_id}/trace"):
        assert outsider.get(path).status_code == 404, path
    assert outsider.get(f"/api/v1/runs?project_id={env.project_id}").status_code == 404
    assert outsider.get("/api/v1/reviews").status_code == 403  # no lead/reviewer role anywhere
    arch, _ = env.as_("arch")
    assert arch.get("/api/v1/reviews").status_code == 403


def test_trace_is_append_only(env: Env, migration_url: str) -> None:
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "改ざん"}).json()["id"]
    engine = create_engine(migration_url)
    for statement in ("UPDATE run_event SET seq = 99 WHERE run_id = :r", "DELETE FROM run_event WHERE run_id = :r"):
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(statement), {"r": run_id})
