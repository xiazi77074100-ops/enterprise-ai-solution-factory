"""Contract tests against contracts/openapi.yaml (P1-04, jp-vuln-assessment checklist B-10, C-01..C-05).

1. Every implemented route is in the contract with the same method, path and operationId; every contract
   operation is either implemented or explicitly pending for a later phase.
2. Authorization matrix generated from x-easf-roles: anonymous / non-member / member without role / member
   with role, for every implemented operation.
3. Every response (success and error) matches the response schema the contract declares for that status.
"""

import copy
import json
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

from app.main import create_app
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

# Contract operations implemented in later phases (Phase 2: runs/reviews/trace; Phase 3+: documents,
# evaluations, reuse, solutions, llm). Removing an entry here is part of implementing it.
PENDING = {
    "listDocuments", "uploadDocument", "downloadDocument",
    "createSolution", "getSolution", "updateSolutionDraft", "validateSolution", "approveSolution", "listSolutions",
    "startRun", "listRuns", "getRun", "listNodeRuns", "getRunTrace", "exportRunResult",
    "listReviewTasks", "getReviewTask", "decideReviewTask",
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
    revision_id: str
    member_ids: dict[str, str]


@dataclass
class Call:
    method: str
    path: str
    body: Callable[[World], Any] | None = None
    project_scoped: bool = False


def _example(kind: str, name: str) -> Any:
    return json.loads((EXAMPLES / kind / name).read_text(encoding="utf-8"))


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
}
SPECIAL = {"login", "logout"}  # covered by test_session_operations_match_contract


def _send(client: TestClient, call: Call, w: World, headers: dict[str, str]) -> Response:
    path = call.path.format(project=w.project_id, revision=w.revision_id)
    body = call.body(w) if call.body else None
    res: Response = client.request(call.method, path, json=body, headers=headers)
    return res


def _session(db_url: str, login_id: str | None) -> tuple[TestClient, dict[str, str]]:
    client = new_client(db_url)
    if login_id is None:
        return client, dict(ORIGIN)
    res = client.post("/api/v1/session", json={"login_id": login_id, "password": PASSWORD}, headers=ORIGIN)
    assert res.status_code == 200
    return client, {**ORIGIN, "X-CSRF-Token": res.json()["csrf_token"]}


@pytest.fixture
def world(db: Session, db_url: str) -> World:  # noqa: F811
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
    return World(project_id=project_id, revision_id=revision.json()["id"], member_ids=ids)


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
