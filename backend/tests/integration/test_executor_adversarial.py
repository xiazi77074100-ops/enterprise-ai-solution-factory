"""P2-04: the Executor under hostile or broken capabilities, crashes and races (run_execution.md §4・§5).

Each case must end in a definite, non-success state (or a correct retry), keep the worker alive, and never
leak input values into error codes or the trace.
"""

import time
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from app.adapters.local import LocalHandler
from app.executor.engine import Executor
from tests import executor_testkit as kit
from tests.integration.test_auth_projects import db, migrated  # noqa: F401  # shared fixtures
from tests.integration.test_runs import Env, env, env_factory  # noqa: F401  # shared fixtures

pytestmark = pytest.mark.db
SECRET = "秘密の入力値-7f3a"


def single_node(capability_id: str, **budget: int) -> dict[str, Any]:
    workflow = kit.workflow(capability_id, {}, **budget)
    workflow["nodes"] = [workflow["nodes"][0]]
    workflow["edges"] = []
    workflow["outputs"] = [{"name": "fields", "from_node": "draft", "from_path": "/fields"}]
    return workflow


def hostile_env(
    env_factory: Callable[..., Env],
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    func: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    timeout_ms: int = 10000,
    retry: dict[str, Any] | None = None,
    config_schema: dict[str, Any] | None = None,
) -> tuple[Env, str]:
    ref = f"testkit.{name}.v1"
    kit.allow_testkit(monkeypatch, extra_refs=(("local", ref),))
    env = env_factory(handlers=kit.handlers({("local", ref): LocalHandler(func)}))
    contract = kit.capability(
        f"testkit.{name}", ref, timeout_ms=timeout_ms, retry=retry, configuration_schema=config_schema
    )
    arch, h = env.as_("arch")
    assert arch.post("/api/v1/capabilities", json=contract, headers=h).status_code == 201
    return env, f"testkit.{name}"


def run_single(env: Env, capability_id: str, config: dict[str, Any] | None = None, **budget: int) -> dict[str, Any]:
    workflow = single_node(capability_id, **budget)
    workflow["nodes"][0]["config"] = config or {}
    sid = env.solution(workflow)
    run_id = env.start(sid, {"text": SECRET}).json()["id"]
    env.executor().run_until_idle()
    run: dict[str, Any] = env.get(f"/api/v1/runs/{run_id}")
    run["nodes"] = env.get(f"/api/v1/runs/{run_id}/nodes")
    run["trace"] = env.get(f"/api/v1/runs/{run_id}/trace?limit=200")["items"]
    return run


def assert_no_leak(run: dict[str, Any]) -> None:
    assert SECRET not in str(run["trace"]) and SECRET not in str(run["nodes"])


def test_endless_loop_is_killed_at_the_timeout(
    env_factory: Callable[..., Env], monkeypatch: pytest.MonkeyPatch
) -> None:
    env, cap = hostile_env(env_factory, monkeypatch, "sleep", kit.sleep_forever, timeout_ms=1500)
    started = time.monotonic()
    run = run_single(env, cap)
    assert time.monotonic() - started < 30
    assert run["status"] == "failed" and run["failure_code"] == "timeout"
    assert run["nodes"][0]["error_code"] == "timeout"
    assert_no_leak(run)


def test_exception_reports_only_its_type(env_factory: Callable[..., Env], monkeypatch: pytest.MonkeyPatch) -> None:
    env, cap = hostile_env(env_factory, monkeypatch, "boom", kit.raise_error)
    run = run_single(env, cap)
    assert run["status"] == "failed" and run["failure_code"] == "node_failed"
    assert run["nodes"][0]["error_code"] == "exception_valueerror"
    assert_no_leak(run)  # the exception message contained the input


def test_output_breaking_the_schema_fails_without_retry(
    env_factory: Callable[..., Env],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env, cap = hostile_env(
        env_factory, monkeypatch, "shape", kit.wrong_shape, retry={"max_attempts": 2, "idempotent": True}
    )
    run = run_single(env, cap)
    assert run["status"] == "failed" and run["failure_code"] == "invalid_output"
    assert run["nodes"][0]["attempt"] == 1  # a wrong answer is not retried


def test_huge_output_is_refused(env_factory: Callable[..., Env], monkeypatch: pytest.MonkeyPatch) -> None:
    env, cap = hostile_env(env_factory, monkeypatch, "huge", kit.huge_output)
    run = run_single(env, cap)
    assert run["status"] == "failed" and run["nodes"][0]["error_code"] == "output_too_large"


def test_child_process_exit_is_a_failure(env_factory: Callable[..., Env], monkeypatch: pytest.MonkeyPatch) -> None:
    env, cap = hostile_env(env_factory, monkeypatch, "exit", kit.hard_exit)
    run = run_single(env, cap)
    assert run["status"] == "failed" and run["nodes"][0]["error_code"] == "crashed"
    # The worker survived: it can still process another run afterwards.
    assert run_single(env, "testkit.draft", {"min_length": 1})["status"] == "succeeded"


def test_transient_failure_is_retried_when_idempotent(
    env_factory: Callable[..., Env],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    env, cap = hostile_env(
        env_factory,
        monkeypatch,
        "flaky",
        kit.flaky,
        retry={"max_attempts": 1, "idempotent": True},
        config_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["marker"],
            "properties": {"marker": {"type": "string"}},
        },
    )
    run = run_single(env, cap, {"marker": str(tmp_path / "marker")})
    assert run["status"] == "succeeded"
    assert run["nodes"][0]["attempt"] == 2
    retried = [e for e in run["trace"] if e["event_type"] == "node.failed"]
    assert len(retried) == 1 and retried[0]["redacted_metadata"]["will_retry"] is True


def test_not_idempotent_is_not_retried(
    env_factory: Callable[..., Env], monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    env, cap = hostile_env(
        env_factory,
        monkeypatch,
        "flaky",
        kit.flaky,
        config_schema={"type": "object", "additionalProperties": False, "properties": {"marker": {"type": "string"}}},
    )
    run = run_single(env, cap, {"marker": str(tmp_path / "marker")})
    assert run["status"] == "failed" and run["nodes"][0]["attempt"] == 1


def test_timeout_caused_by_the_duration_budget_is_reported_as_budget(
    env_factory: Callable[..., Env],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env, cap = hostile_env(env_factory, monkeypatch, "sleep", kit.sleep_forever, timeout_ms=60000)
    started = time.monotonic()
    run = run_single(env, cap, max_duration_ms=1500)
    assert time.monotonic() - started < 30  # cut at the remaining budget, not at the 60 s capability timeout
    assert run["status"] == "failed" and run["failure_code"] == "budget_exceeded"


def test_input_breaking_the_node_schema_fails_the_run(env: Env) -> None:
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "x" * 2000}).json()["id"]  # the node accepts at most 1000 characters
    env.executor().run_until_idle()
    run = env.get(f"/api/v1/runs/{run_id}")
    assert run["status"] == "failed" and run["failure_code"] == "invalid_input"
    assert env.start(sid, {"text": "x" * 10001}).status_code == 422  # run inputs are bounded too


def test_worker_crash_mid_call_is_recovered(env: Env, migration_url: str) -> None:
    sid = env.solution(kit.workflow())
    run_id = env.start(sid, {"text": "中断からの回復"}).json()["id"]
    engine = create_engine(migration_url)
    with engine.begin() as conn:  # what a worker leaves behind when it dies during the draft call
        conn.execute(
            text(
                "UPDATE run SET status = 'running', started_at = now(), "
                "lease_until = now() - interval '1 minute' WHERE id = :r"
            ),
            {"r": run_id},
        )
        conn.execute(
            text("UPDATE node_run SET status = 'running', started_at = now() WHERE run_id = :r AND node_id = 'draft'"),
            {"r": run_id},
        )
    env.executor().run_until_idle()
    nodes = {n["node_id"]: n for n in env.get(f"/api/v1/runs/{run_id}/nodes")}
    assert nodes["draft"]["status"] == "succeeded" and nodes["draft"]["attempt"] == 2  # idempotent: retried
    assert env.get(f"/api/v1/runs/{run_id}")["status"] == "waiting_review"
    interrupted = [e for e in env.get(f"/api/v1/runs/{run_id}/trace")["items"] if e["event_type"] == "node.failed"]
    assert interrupted[0]["redacted_metadata"]["error_code"] == "interrupted"


def test_two_workers_never_claim_the_same_run(env: Env) -> None:
    sid = env.solution(kit.workflow())
    env.start(sid, {"text": "取り合い"})
    first, second = env.executor(), env.executor()
    claimed = first._claim()
    assert claimed is not None
    assert second._claim() is None  # leased by the first worker
    assert isinstance(claimed, uuid.UUID)


def test_review_of_another_run_is_not_found(env: Env) -> None:
    sid = env.solution(kit.workflow())
    runs = [env.start(sid, {"text": f"別の実行{i}"}).json()["id"] for i in range(2)]
    env.executor().run_until_idle()
    task = env.review_of(runs[0])
    who = "reviewer" if task["assigned_to"] == env.users["reviewer"] else "reviewer2"
    res = env.decide(runs[1], task["id"], {"decision": "approved"}, who=who)
    assert res.status_code == 404


def test_executor_is_idle_when_nothing_is_claimable(env: Env) -> None:
    assert Executor(env.executor().session_factory, env.handlers).run_once() is False
