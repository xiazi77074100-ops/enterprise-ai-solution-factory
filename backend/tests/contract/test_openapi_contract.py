"""Contract tests against contracts/openapi.yaml (P1-04, jp-vuln-assessment checklist B-10, C-01..C-05).

1. Every implemented route is in the contract with the same method, path and operationId; every contract
   operation is either implemented or explicitly pending for a later phase.
2. Authorization matrix generated from x-easf-roles: anonymous / non-member / member without role / member
   with role, for every implemented operation.
3. Every response (success and error) matches the response schema the contract declares for that status.
"""

import copy
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from httpx import Response
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy.orm import Session

from app import main as main_module
from app.core.db import make_session_factory
from app.executor.engine import Executor
from app.main import create_app
from tests import executor_testkit as kit
from tests.conftest import make_settings
from tests.integration.test_auth_projects import (  # noqa: F401  # shared fixtures
    ORIGIN,
    PASSWORD,
    db,
    make_user,
    migrated,
    new_client,
)

ROOT = Path(__file__).resolve().parents[3]
OPENAPI: dict[str, Any] = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
EXAMPLES = ROOT / "contracts" / "examples"
METHODS = ("get", "post", "put", "delete", "patch")

# Contract operations implemented in later phases (Phase 2: runs/reviews/trace; Phase 3+: documents, export,
# evaluations, reuse, llm). Removing an entry here is part of implementing it.
PENDING = {
    "listDocuments", "uploadDocument", "downloadDocument",
    "exportRunResult",
    "listDatasetVersions", "startEvaluation", "getEvaluation", "listEvaluations",
    "getProjectReuseEvidence", "getReuseSummary", "createReuseRecord",
    "listLlmProfiles",
}  # fmt: skip


def contract_operations() -> dict[str, tuple[str, str, dict[str, Any]]]:
    ops = {}
    for path, item in OPENAPI["paths"].items():
        for method in METHODS:
            if method in item:
                ops[item[method]["operationId"]] = (method.upper(), path, item[method])
    return ops


CONTRACT = contract_operations()


def test_implemented_routes_match_contract() -> None:
    # The implementation's own OpenAPI (generated even when /openapi.json is not served).
    generated = create_app(make_settings()).openapi()
    implemented = {
        op["operationId"]: (method.upper(), path)
        for path, item in generated["paths"].items()
        for method, op in item.items()
        if method in METHODS
    }
    assert implemented, "no routes found"
    for op_id, (method, path) in implemented.items():
        assert op_id in CONTRACT, f"{op_id} is not in the contract"
        assert CONTRACT[op_id][:2] == (method, path), f"{op_id}: {method} {path} != contract {CONTRACT[op_id][:2]}"
    assert set(CONTRACT) == set(implemented) | PENDING, set(CONTRACT) ^ (set(implemented) | PENDING)
    assert not set(implemented) & PENDING, "implemented operations must be removed from PENDING"


# --- response schema validation -------------------------------------------------------------------


def _resolve(obj: dict[str, Any]) -> dict[str, Any]:
    ref = obj.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/responses/"):
        resolved: dict[str, Any] = OPENAPI["components"]["responses"][ref.rsplit("/", 1)[1]]
        return resolved
    return obj


def assert_matches_contract(op_id: str, res: Response) -> None:
    _, _, op = CONTRACT[op_id]
    declared = op["responses"].get(str(res.status_code))
    assert declared is not None, f"{op_id}: status {res.status_code} is not declared in the contract ({res.text[:200]})"
    content = _resolve(declared).get("content")
    if not content:
        assert res.content in (b"", b"null"), f"{op_id}: {res.status_code} must have no body"
        return
    schema = content.get("application/json", {}).get("schema")
    if schema is None:
        return  # non-JSON media (file download) is checked by its own tests
    wrapped = {**copy.deepcopy(schema), "components": OPENAPI["components"]}
    errors = sorted(Draft202012Validator(wrapped, format_checker=FormatChecker()).iter_errors(res.json()), key=str)
    assert not errors, f"{op_id} {res.status_code}: {[e.message for e in errors][:5]}"


# --- authorization matrix ---------------------------------------------------------------------------


@dataclass
class World:
    project_id: str
    revision_id: str  # not approved (approveRequirementRevision)
    member_ids: dict[str, str]
    approved_revision_id: str = ""
    solution_id: str = ""  # validated, created by the architect
    solution_etag: str = ""
    runnable_solution_id: str = ""  # approved testkit workflow
    run_id: str = ""  # waiting for review
    review_id: str = ""  # assigned to "reviewer"


@dataclass
class Call:
    method: str
    path: str
    body: Callable[[World], Any] | None = None
    project_scoped: bool = False
    headers: Callable[[World], dict[str, str]] | None = None


def _example(kind: str, name: str) -> Any:
    return json.loads((EXAMPLES / kind / name).read_text(encoding="utf-8"))


def _single_node_workflow() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "workflow_id": "contract-test",
        "version": 1,
        "name": "契約テスト",
        "inputs": [{"name": "doc", "type": "document_ref", "to": [{"node_id": "parse", "field": "document_ref"}]}],
        "nodes": [
            {
                "node_id": "parse",
                "capability_id": "document.parser",
                "capability_version": "1.0.0",
                "config": {"ocr": "none"},
            }
        ],
        "edges": [],
        "outputs": [{"name": "document_id", "from_node": "parse", "from_path": "/document_id"}],
        "budget": {"max_duration_ms": 60000, "max_llm_tokens": 0, "max_cost_jpy": 0},
        "requires_human_approval": True,
    }


def _solution_create(w: World) -> dict[str, Any]:
    return {
        "project_id": w.project_id,
        "requirement_revision_id": w.approved_revision_id,
        "workflow": _single_node_workflow(),
    }


def _members(w: World) -> list[dict[str, Any]]:
    return [
        {"user_id": w.member_ids["lead"], "roles": ["solution_lead"]},
        {"user_id": w.member_ids["arch"], "roles": ["solution_architect"]},
        {"user_id": w.member_ids["reviewer"], "roles": ["business_reviewer"]},
    ]


CALLS: dict[str, Call] = {
    "getHealth": Call("GET", "/health"),
    "getReady": Call("GET", "/ready"),
    "getSession": Call("GET", "/api/v1/session"),
    "listProjects": Call("GET", "/api/v1/projects"),
    "createProject": Call("POST", "/api/v1/projects", lambda w: {"name": "新規", "business_domain": "経理"}),
    "getProject": Call("GET", "/api/v1/projects/{project}", project_scoped=True),
    "listRequirementRevisions": Call("GET", "/api/v1/projects/{project}/requirements", project_scoped=True),
    "createRequirementRevision": Call(
        "POST", "/api/v1/projects/{project}/requirements", lambda w: {"content": "要件"}, project_scoped=True
    ),
    "approveRequirementRevision": Call("POST", "/api/v1/requirements/{revision}/approve", project_scoped=True),
    "getProjectMembers": Call("GET", "/api/v1/projects/{project}/members", project_scoped=True),
    "putProjectMembers": Call("PUT", "/api/v1/projects/{project}/members", _members, project_scoped=True),
    "listCapabilities": Call("GET", "/api/v1/capabilities"),
    "registerCapabilityVersion": Call(
        "POST", "/api/v1/capabilities", lambda w: _example("capabilities", "document_parser.json")
    ),
    "validateCapabilityContract": Call(
        "POST", "/api/v1/capabilities/validate", lambda w: _example("capabilities", "document_parser.json")
    ),
    "getCapabilityVersion": Call("GET", "/api/v1/capabilities/document.parser/versions/1.0.0"),
    "listRulePacks": Call("GET", "/api/v1/rule-packs"),
    "registerRulePackVersion": Call(
        "POST", "/api/v1/rule-packs", lambda w: _example("rule_packs", "invoice-1.0.0.json")
    ),
    "getRulePackVersion": Call("GET", "/api/v1/rule-packs/invoice/versions/1.0.0"),
    "createSolution": Call("POST", "/api/v1/solutions", _solution_create, project_scoped=True),
    "getSolution": Call("GET", "/api/v1/solutions/{solution}", project_scoped=True),
    "updateSolutionDraft": Call(
        "PUT",
        "/api/v1/solutions/{solution}",
        lambda w: {"workflow": _single_node_workflow() | {"name": "更新"}},
        project_scoped=True,
        headers=lambda w: {"If-Match": w.solution_etag},
    ),
    "validateSolution": Call("POST", "/api/v1/solutions/{solution}/validate", project_scoped=True),
    "approveSolution": Call("POST", "/api/v1/solutions/{solution}/approve", project_scoped=True),
    "listSolutions": Call("GET", "/api/v1/projects/{project}/solutions", project_scoped=True),
    "startRun": Call(
        "POST",
        "/api/v1/solutions/{runnable}/runs",
        lambda w: {"inputs": {"text": "契約テスト"}},
        project_scoped=True,
        headers=lambda w: {"Idempotency-Key": str(uuid.uuid4())},
    ),
    "listRuns": Call("GET", "/api/v1/runs?project_id={project}", project_scoped=True),
    "getRun": Call("GET", "/api/v1/runs/{run}", project_scoped=True),
    "listNodeRuns": Call("GET", "/api/v1/runs/{run}/nodes", project_scoped=True),
    "getRunTrace": Call("GET", "/api/v1/runs/{run}/trace", project_scoped=True),
    "listReviewTasks": Call("GET", "/api/v1/reviews"),
    "getReviewTask": Call("GET", "/api/v1/runs/{run}/reviews/{review}", project_scoped=True),
    "decideReviewTask": Call(
        "POST",
        "/api/v1/runs/{run}/reviews/{review}/decision",
        lambda w: {"decision": "approved"},
        project_scoped=True,
        headers=lambda w: {"Idempotency-Key": str(uuid.uuid4())},
    ),
}
SPECIAL = {"login", "logout"}  # covered by test_session_operations_match_contract


def _send(client: TestClient, call: Call, w: World, headers: dict[str, str]) -> Response:
    path = call.path.format(
        project=w.project_id,
        revision=w.revision_id,
        solution=w.solution_id,
        runnable=w.runnable_solution_id,
        run=w.run_id,
        review=w.review_id,
    )
    body = call.body(w) if call.body else None
    extra = call.headers(w) if call.headers else {}
    res: Response = client.request(call.method, path, json=body, headers={**headers, **extra})
    return res


def _session(db_url: str, login_id: str | None) -> tuple[TestClient, dict[str, str]]:
    client = new_client(db_url)
    if login_id is None:
        return client, dict(ORIGIN)
    res = client.post("/api/v1/session", json={"login_id": login_id, "password": PASSWORD}, headers=ORIGIN)
    assert res.status_code == 200
    return client, {**ORIGIN, "X-CSRF-Token": res.json()["csrf_token"]}


@pytest.fixture
def world(db: Session, db_url: str, monkeypatch: pytest.MonkeyPatch) -> World:  # noqa: F811
    # Test-only capabilities so run and review operations can be exercised (PHASE2_PLAN §3).
    kit.allow_testkit(monkeypatch)
    monkeypatch.setattr(main_module, "production_handlers", kit.handlers)
    users = {name: make_user(db, name) for name in ("lead", "arch", "reviewer", "outsider")}
    admin = make_user(db, "admin", admin=True)
    client, headers = _session(db_url, "admin")
    project_id = client.post(
        "/api/v1/projects", json={"name": "対象", "business_domain": "経理"}, headers=headers
    ).json()["id"]
    ids = {k: str(u.id) for k, u in users.items()}
    members = [{"user_id": str(admin.id), "roles": ["solution_lead"]}] + _members(World("", "", ids))
    assert client.put(f"/api/v1/projects/{project_id}/members", json=members, headers=headers).status_code == 200
    arch_client, arch_headers = _session(db_url, "arch")
    revision = arch_client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"content": "要件"}, headers=arch_headers
    )
    assert (
        arch_client.post(
            "/api/v1/capabilities", json=_example("capabilities", "document_parser.json"), headers=arch_headers
        ).status_code
        == 201
    )
    assert (
        arch_client.post(
            "/api/v1/rule-packs", json=_example("rule_packs", "invoice-1.0.0.json"), headers=arch_headers
        ).status_code
        == 201
    )
    approved = arch_client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"content": "承認済みの要件"}, headers=arch_headers
    ).json()["id"]
    assert client.post(f"/api/v1/requirements/{approved}/approve", headers=headers).status_code == 200
    w = World(project_id=project_id, revision_id=revision.json()["id"], member_ids=ids, approved_revision_id=approved)
    created = arch_client.post("/api/v1/solutions", json=_solution_create(w), headers=arch_headers)
    assert created.status_code == 201, created.text
    w.solution_id, w.solution_etag = created.json()["id"], created.headers["etag"]
    report = arch_client.post(f"/api/v1/solutions/{w.solution_id}/validate", headers=arch_headers).json()
    assert report["valid"], report

    for contract in [*kit.CONTRACTS.values(), kit.human_review()]:
        assert arch_client.post("/api/v1/capabilities", json=contract, headers=arch_headers).status_code == 201
    body = {"project_id": project_id, "requirement_revision_id": approved, "workflow": kit.workflow()}
    w.runnable_solution_id = arch_client.post("/api/v1/solutions", json=body, headers=arch_headers).json()["id"]
    assert arch_client.post(f"/api/v1/solutions/{w.runnable_solution_id}/validate", headers=arch_headers).json()[
        "valid"
    ]
    approved_solution = client.post(f"/api/v1/solutions/{w.runnable_solution_id}/approve", headers=headers)
    assert approved_solution.status_code == 200, approved_solution.text
    started = client.post(
        f"/api/v1/solutions/{w.runnable_solution_id}/runs",
        json={"inputs": {"text": "確認待ち"}},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert started.status_code == 202, started.text
    w.run_id = started.json()["id"]
    Executor(make_session_factory(make_settings(database_url=db_url)), kit.handlers()).run_until_idle()
    reviewer_client, _ = _session(db_url, "reviewer")
    tasks = reviewer_client.get("/api/v1/reviews").json()["items"]
    w.review_id = next(t["id"] for t in tasks if t["run_id"] == w.run_id)
    return w


ROLE_USER = {"solution_lead": "lead", "solution_architect": "arch", "business_reviewer": "reviewer", "admin": "admin"}


def test_matrix_covers_every_implemented_operation() -> None:
    implemented = set(CONTRACT) - PENDING
    assert implemented == set(CALLS) | SPECIAL, implemented ^ (set(CALLS) | SPECIAL)


@pytest.mark.db
@pytest.mark.parametrize("op_id", sorted(CALLS))
def test_authorization_matrix(op_id: str, world: World, db_url: str) -> None:
    call = CALLS[op_id]
    roles = set(CONTRACT[op_id][2]["x-easf-roles"])

    anonymous = _send(*_session(db_url, None)[:1], call, world, dict(ORIGIN))
    assert_matches_contract(op_id, anonymous)
    if "public" in roles:
        assert anonymous.status_code < 400, anonymous.text
        return
    assert anonymous.status_code == 401, f"{op_id}: anonymous got {anonymous.status_code}"

    client, headers = _session(db_url, "outsider")
    outsider = _send(client, call, world, headers)
    assert_matches_contract(op_id, outsider)
    if "any_authenticated" in roles:
        assert outsider.status_code < 400, outsider.text
        return
    expected_outsider = 404 if call.project_scoped else 403
    assert outsider.status_code == expected_outsider, f"{op_id}: outsider got {outsider.status_code}"

    if roles == {"project_member"}:
        allowed_users, denied_users = ["reviewer"], []
    else:
        allowed_users = [ROLE_USER[r] for r in roles if r in ROLE_USER]
        denied_users = [u for u in ("lead", "arch", "reviewer") if u not in allowed_users]
    for user in denied_users:
        client, headers = _session(db_url, user)
        res = _send(client, call, world, headers)
        assert_matches_contract(op_id, res)
        assert res.status_code == 403, f"{op_id}: {user} (no role) got {res.status_code}"
    for user in allowed_users:
        client, headers = _session(db_url, user)
        res = _send(client, call, world, headers)
        assert_matches_contract(op_id, res)
        assert res.status_code < 400, f"{op_id}: {user} got {res.status_code} {res.text[:200]}"


@pytest.mark.db
def test_session_operations_match_contract(world: World, db_url: str) -> None:
    client = new_client(db_url)
    bad = client.post("/api/v1/session", json={"login_id": "lead", "password": "wrong"}, headers=ORIGIN)
    assert bad.status_code == 401
    assert_matches_contract("login", bad)
    no_origin = client.post("/api/v1/session", json={"login_id": "lead", "password": PASSWORD})
    assert no_origin.status_code == 403
    assert_matches_contract("login", no_origin)
    ok = client.post("/api/v1/session", json={"login_id": "lead", "password": PASSWORD}, headers=ORIGIN)
    assert_matches_contract("login", ok)
    headers = {**ORIGIN, "X-CSRF-Token": ok.json()["csrf_token"]}
    no_csrf = client.delete("/api/v1/session", headers=ORIGIN)
    assert no_csrf.status_code == 403
    assert_matches_contract("logout", no_csrf)
    out = client.delete("/api/v1/session", headers=headers)
    assert out.status_code == 204
    assert_matches_contract("logout", out)
    again = client.delete("/api/v1/session", headers=headers)
    assert again.status_code == 401
    assert_matches_contract("logout", again)


def test_role_restricted_operations_declare_403() -> None:
    """D-025: an operation limited to specific roles must declare the 403 it returns to other members."""
    open_roles = {"public", "any_authenticated", "project_member"}
    missing = [
        op_id
        for op_id, (_, _, op) in CONTRACT.items()
        if set(op["x-easf-roles"]) - open_roles and "403" not in op["responses"]
    ]
    assert missing == []
