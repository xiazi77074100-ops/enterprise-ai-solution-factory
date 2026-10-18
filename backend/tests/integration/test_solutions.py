"""Solutions API (run_execution.md §1): draft → validated → approved, ETag/If-Match, freezing, permissions."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration.test_auth_projects import (  # noqa: F401  # shared fixtures
    ORIGIN,
    PASSWORD,
    db,
    make_user,
    migrated,
    new_client,
)

pytestmark = pytest.mark.db
EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"


def login(db_url: str, login_id: str) -> tuple[TestClient, dict[str, str]]:
    client = new_client(db_url)
    res = client.post("/api/v1/session", json={"login_id": login_id, "password": PASSWORD}, headers=ORIGIN)
    assert res.status_code == 200, res.text
    return client, {**ORIGIN, "X-CSRF-Token": res.json()["csrf_token"]}


def example(kind: str, name: str) -> Any:
    return json.loads((EXAMPLES / kind / name).read_text(encoding="utf-8"))


@pytest.fixture
def setup(db: Session, db_url: str) -> dict[str, Any]:  # noqa: F811
    users = {name: make_user(db, name) for name in ("lead", "arch", "reviewer", "outsider")}
    admin_user = make_user(db, "admin", admin=True)
    admin, admin_h = login(db_url, "admin")
    project = admin.post("/api/v1/projects", json={"name": "案件", "business_domain": "経理"}, headers=admin_h).json()
    members = [
        {"user_id": str(admin_user.id), "roles": ["solution_lead"]},
        {"user_id": str(users["lead"].id), "roles": ["solution_lead"]},
        {"user_id": str(users["arch"].id), "roles": ["solution_architect"]},
        {"user_id": str(users["reviewer"].id), "roles": ["business_reviewer"]},
    ]
    assert admin.put(f"/api/v1/projects/{project['id']}/members", json=members, headers=admin_h).status_code == 200
    lead, lead_h = login(db_url, "lead")
    arch, arch_h = login(db_url, "arch")
    for path in sorted((EXAMPLES / "capabilities").glob("*.json")):
        res = arch.post("/api/v1/capabilities", json=json.loads(path.read_text(encoding="utf-8")), headers=arch_h)
        assert res.status_code == 201, res.text
    for path in sorted((EXAMPLES / "rule_packs").glob("*.json")):
        res = arch.post("/api/v1/rule-packs", json=json.loads(path.read_text(encoding="utf-8")), headers=arch_h)
        assert res.status_code == 201, res.text
    requirement = arch.post(
        f"/api/v1/projects/{project['id']}/requirements", json={"content": "要件"}, headers=arch_h
    ).json()
    return {
        "project": project["id"],
        "requirement": requirement["id"],
        "lead": (lead, lead_h),
        "arch": (arch, arch_h),
        "reviewer": login(db_url, "reviewer"),
        "outsider": login(db_url, "outsider"),
    }


def create(s: dict[str, Any], workflow: dict[str, Any] | None = None) -> Any:
    arch, h = s["arch"]
    body = {
        "project_id": s["project"],
        "requirement_revision_id": s["requirement"],
        "workflow": workflow or example("workflows", "invoice.json"),
    }
    return arch.post("/api/v1/solutions", json=body, headers=h)


def test_full_lifecycle(setup: dict[str, Any]) -> None:
    s = setup
    arch, arch_h = s["arch"]
    lead, lead_h = s["lead"]
    created = create(s)
    assert created.status_code == 201, created.text
    solution = created.json()
    sid, etag = solution["id"], created.headers["etag"]
    assert solution["state"] == "draft" and solution["approved_by"] is None
    assert etag == f'"{solution["workflow_hash"]}:1"'

    report = arch.post(f"/api/v1/solutions/{sid}/validate", headers=arch_h).json()
    assert report["valid"] is True and report["errors"] == []
    assert {w["code"] for w in report["warnings"]} == {"implementation_unavailable"}
    assert arch.get(f"/api/v1/solutions/{sid}").json()["state"] == "validated"

    # Approval needs an approved requirement revision and an approver other than the author.
    assert lead.post(f"/api/v1/solutions/{sid}/approve", headers=lead_h).json()["code"] == "requirement_not_approved"
    approved_req = lead.post(f"/api/v1/requirements/{s['requirement']}/approve", headers=lead_h)
    assert approved_req.status_code == 200
    approved = lead.post(f"/api/v1/solutions/{sid}/approve", headers=lead_h)
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "approved" and approved.json()["workflow_hash"] == solution["workflow_hash"]
    again = lead.post(f"/api/v1/solutions/{sid}/approve", headers=lead_h)
    assert again.status_code == 409

    current = arch.get(f"/api/v1/solutions/{sid}")
    frozen = arch.put(
        f"/api/v1/solutions/{sid}",
        json={"workflow": solution["workflow"]},
        headers={**arch_h, "If-Match": current.headers["etag"]},
    )
    assert frozen.status_code == 409 and frozen.json()["code"] == "solution_frozen"


def test_update_requires_current_etag_and_returns_to_draft(setup: dict[str, Any]) -> None:
    arch, h = setup["arch"]
    created = create(setup)
    sid, etag = created.json()["id"], created.headers["etag"]
    assert arch.post(f"/api/v1/solutions/{sid}/validate", headers=h).json()["valid"] is True
    workflow = created.json()["workflow"] | {"name": "変更後"}

    stale = arch.put(f"/api/v1/solutions/{sid}", json={"workflow": workflow}, headers={**h, "If-Match": '"x:0"'})
    assert stale.status_code == 412
    missing = arch.put(f"/api/v1/solutions/{sid}", json={"workflow": workflow}, headers=h)
    assert missing.status_code == 422

    updated = arch.put(f"/api/v1/solutions/{sid}", json={"workflow": workflow}, headers={**h, "If-Match": etag})
    assert updated.status_code == 200, updated.text
    assert updated.json()["state"] == "draft"
    assert updated.json()["workflow_hash"] != created.json()["workflow_hash"]
    assert updated.headers["etag"].endswith(':2"')
    # The old ETag is no longer valid.
    replay = arch.put(f"/api/v1/solutions/{sid}", json={"workflow": workflow}, headers={**h, "If-Match": etag})
    assert replay.status_code == 412


def test_invalid_workflow_stays_draft_and_cannot_be_approved(setup: dict[str, Any]) -> None:
    arch, arch_h = setup["arch"]
    lead, lead_h = setup["lead"]
    workflow = example("workflows", "invoice.json")
    workflow["edges"].append(
        {"from": "export", "to": "parse", "mapping": [{"from_path": "/format", "to_field": "document_ref"}]}
    )
    sid = create(setup, workflow).json()["id"]
    report = arch.post(f"/api/v1/solutions/{sid}/validate", headers=arch_h).json()
    assert report["valid"] is False
    assert "cycle" in {e["code"] for e in report["errors"]}
    assert arch.get(f"/api/v1/solutions/{sid}").json()["state"] == "draft"
    lead.post(f"/api/v1/requirements/{setup['requirement']}/approve", headers=lead_h)
    res = lead.post(f"/api/v1/solutions/{sid}/approve", headers=lead_h)
    assert res.status_code == 409 and res.json()["code"] == "not_validated"


def test_permissions_and_isolation(setup: dict[str, Any]) -> None:
    arch, arch_h = setup["arch"]
    lead, lead_h = setup["lead"]
    reviewer, reviewer_h = setup["reviewer"]
    outsider, outsider_h = setup["outsider"]
    sid = create(setup).json()["id"]

    assert create({**setup, "arch": setup["lead"]}).status_code == 403  # lead is not an architect
    assert create({**setup, "arch": setup["outsider"]}).status_code == 404  # not a member
    assert outsider.get(f"/api/v1/solutions/{sid}").status_code == 404
    assert outsider.get(f"/api/v1/projects/{setup['project']}/solutions").status_code == 404
    assert reviewer.get(f"/api/v1/solutions/{sid}").status_code == 200
    assert reviewer.post(f"/api/v1/solutions/{sid}/validate", headers=reviewer_h).status_code == 403
    assert arch.post(f"/api/v1/solutions/{sid}/validate", headers=arch_h).status_code == 200
    lead.post(f"/api/v1/requirements/{setup['requirement']}/approve", headers=lead_h)
    assert arch.post(f"/api/v1/solutions/{sid}/approve", headers=arch_h).status_code == 403  # not a lead

    # A requirement revision of another project is rejected.
    other = lead.post("/api/v1/projects", json={"name": "別案件", "business_domain": "経理"}, headers=lead_h).json()
    lead_members = [{"user_id": m["user_id"], "roles": ["solution_lead", "solution_architect"]}
                    for m in lead.get(f"/api/v1/projects/{other['id']}/members").json()]  # fmt: skip
    lead.put(f"/api/v1/projects/{other['id']}/members", json=lead_members, headers=lead_h)
    foreign = lead.post(f"/api/v1/projects/{other['id']}/requirements", json={"content": "x"}, headers=lead_h).json()
    res = create({**setup, "requirement": foreign["id"]})
    assert res.status_code == 422 and res.json()["code"] == "unknown_requirement_revision"

    listed = reviewer.get(f"/api/v1/projects/{setup['project']}/solutions").json()
    assert [i["id"] for i in listed["items"]] == [sid] and listed["page"]["total"] == 1


def test_database_rejects_changes_to_approved_solution(setup: dict[str, Any], migration_url: str) -> None:
    arch, arch_h = setup["arch"]
    lead, lead_h = setup["lead"]
    sid = create(setup).json()["id"]
    arch.post(f"/api/v1/solutions/{sid}/validate", headers=arch_h)
    lead.post(f"/api/v1/requirements/{setup['requirement']}/approve", headers=lead_h)
    assert lead.post(f"/api/v1/solutions/{sid}/approve", headers=lead_h).status_code == 200
    engine = create_engine(migration_url)
    for statement in (
        "UPDATE solution SET workflow = '{}'::jsonb WHERE id = :id",
        "UPDATE solution SET state = 'draft' WHERE id = :id",
        "DELETE FROM solution WHERE id = :id",
    ):
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(statement), {"id": sid})
