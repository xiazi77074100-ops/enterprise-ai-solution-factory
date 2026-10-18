"""Capability Catalog (FR-03 / AC-02): immutable versions, idempotency, validation, permissions."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration.test_auth_projects import (  # noqa: F401  # shared fixtures and helpers
    ORIGIN,
    app_client,
    create_project,
    db,
    login,
    make_user,
    migrated,
    new_client,
)

pytestmark = pytest.mark.db
EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"


def load(kind: str, name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLES / kind / name).read_text(encoding="utf-8"))
    return data


def architect(app_client: TestClient, db: Session, db_url: str) -> tuple[TestClient, dict[str, str]]:  # noqa: F811
    admin = make_user(db, "admin", admin=True)
    arch = make_user(db, "arch")
    admin_headers = login(app_client, "admin")
    project_id = create_project(app_client, admin_headers)
    members = [
        {"user_id": str(admin.id), "roles": ["solution_lead"]},
        {"user_id": str(arch.id), "roles": ["solution_architect"]},
    ]
    assert (
        app_client.put(f"/api/v1/projects/{project_id}/members", json=members, headers=admin_headers).status_code == 200
    )
    client = new_client(db_url)
    return client, login(client, "arch")


def test_register_all_examples_and_idempotency(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    client, headers = architect(app_client, db, db_url)
    ids = {}
    for path in sorted((EXAMPLES / "capabilities").glob("*.json")):
        contract = load("capabilities", path.name)
        res = client.post("/api/v1/capabilities", json=contract, headers=headers)
        assert res.status_code == 201, (path.name, res.text)
        ids[path.name] = res.json()["id"]
    # same content with keys in a different order -> same canonical hash -> 200, same row
    contract = load("capabilities", "document_parser.json")
    reordered = dict(reversed(list(contract.items())))
    again = client.post("/api/v1/capabilities", json=reordered, headers=headers)
    assert again.status_code == 200 and again.json()["id"] == ids["document_parser.json"]


def test_changed_content_same_version_is_conflict(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    client, headers = architect(app_client, db, db_url)
    contract = load("capabilities", "document_parser.json")
    assert client.post("/api/v1/capabilities", json=contract, headers=headers).status_code == 201
    changed = {**contract, "description": "内容を変えた"}
    res = client.post("/api/v1/capabilities", json=changed, headers=headers)
    assert res.status_code == 409 and res.json()["code"] == "version_conflict"
    bumped = {**changed, "version": "1.0.1"}
    assert client.post("/api/v1/capabilities", json=bumped, headers=headers).status_code == 201


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda c: c["input_schema"]["properties"].update(x={"$ref": "http://127.0.0.1:5432/x"}), "external_ref"),
        (lambda c: c["implementation"].update(ref="os.system"), "unknown_implementation"),
        (lambda c: c.update(retry={"max_attempts": 2, "idempotent": False}), "schema_violation"),
        (lambda c: c.update(owner="someone"), "schema_violation"),
        (lambda c: c.update(side_effects=True), "schema_violation"),
        (lambda c: c.update(version="^1.0"), "schema_violation"),
        (lambda c: c["output_schema"].update(type="string"), "schema_violation"),
    ],
)
def test_invalid_contracts_are_rejected(
    app_client: TestClient,  # noqa: F811
    db: Session,  # noqa: F811
    db_url: str,
    mutate: Any,
    reason: str,
) -> None:
    client, headers = architect(app_client, db, db_url)
    contract = copy.deepcopy(load("capabilities", "document_parser.json"))
    mutate(contract)
    res = client.post("/api/v1/capabilities", json=contract, headers=headers)
    assert res.status_code == 422, res.text
    assert reason in {d["reason"] for d in res.json()["details"]}
    assert client.get("/api/v1/capabilities").json()["page"]["total"] == 0


def test_validate_endpoint_has_no_side_effects(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    client, headers = architect(app_client, db, db_url)
    bad = load("capabilities", "document_parser.json") | {"kind": "shell"}
    report = client.post("/api/v1/capabilities/validate", json=bad, headers=headers).json()
    assert report["valid"] is False and report["errors"]
    good = client.post(
        "/api/v1/capabilities/validate", json=load("capabilities", "rule_validator.json"), headers=headers
    )
    assert good.json() == {"valid": True, "errors": [], "warnings": []}
    assert client.get("/api/v1/capabilities").json()["page"]["total"] == 0


def test_permissions(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    make_user(db, "viewer")
    viewer = new_client(db_url)
    viewer_headers = login(viewer, "viewer")
    contract = load("capabilities", "document_parser.json")
    assert viewer.post("/api/v1/capabilities", json=contract, headers=viewer_headers).status_code == 403
    assert (
        viewer.post(
            "/api/v1/rule-packs", json=load("rule_packs", "invoice-1.0.0.json"), headers=viewer_headers
        ).status_code
        == 403
    )
    assert viewer.get("/api/v1/capabilities").status_code == 200  # read: any authenticated user
    anonymous = new_client(db_url)
    assert anonymous.get("/api/v1/capabilities").status_code == 401
    assert anonymous.post("/api/v1/capabilities", json=contract, headers=ORIGIN).status_code == 401
    client, headers = architect(app_client, db, db_url)
    assert client.post("/api/v1/capabilities", json=contract, headers=ORIGIN).status_code == 403  # no CSRF token
    assert client.post("/api/v1/capabilities", json=[contract], headers=headers).status_code == 422


def test_list_filters_and_get(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    client, headers = architect(app_client, db, db_url)
    for name in ("document_parser.json", "structured_extractor.json", "evidence_locator.json"):
        client.post("/api/v1/capabilities", json=load("capabilities", name), headers=headers)
    assert client.get("/api/v1/capabilities", params={"kind": "llm"}).json()["page"]["total"] == 1
    assert client.get("/api/v1/capabilities", params={"tag": "document"}).json()["page"]["total"] == 3
    assert client.get("/api/v1/capabilities", params={"q": "evidence"}).json()["page"]["total"] == 1
    assert client.get("/api/v1/capabilities", params={"kind": "shell"}).status_code == 422
    got = client.get("/api/v1/capabilities/document.parser/versions/1.0.0")
    assert got.status_code == 200 and got.json()["contract"]["capability_id"] == "document.parser"
    assert len(got.json()["content_sha256"]) == 64
    assert client.get("/api/v1/capabilities/document.parser/versions/9.9.9").status_code == 404
    assert client.get("/api/v1/capabilities/document.parser/versions/latest").status_code == 422


def test_database_rejects_mutation_of_registered_versions(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    client, headers = architect(app_client, db, db_url)
    client.post("/api/v1/capabilities", json=load("capabilities", "document_parser.json"), headers=headers)
    for statement in ("UPDATE capability_version SET name = 'changed'", "DELETE FROM capability_version"):
        with pytest.raises(DBAPIError, match="immutable row"):
            db.execute(text(statement))
        db.rollback()


def test_rule_packs(app_client: TestClient, db: Session, db_url: str) -> None:  # noqa: F811
    client, headers = architect(app_client, db, db_url)
    for name in ("invoice-1.0.0.json", "contract-1.0.0.json"):
        assert client.post("/api/v1/rule-packs", json=load("rule_packs", name), headers=headers).status_code == 201
    assert (
        client.post("/api/v1/rule-packs", json=load("rule_packs", "invoice-1.0.0.json"), headers=headers).status_code
        == 200
    )
    got = client.get("/api/v1/rule-packs/invoice/versions/1.0.0")
    assert got.status_code == 200 and len(got.json()["rule_pack"]["rules"]) == 6
    assert client.get("/api/v1/rule-packs").json()["page"]["total"] == 2

    deep: dict[str, Any] = {"op": "present", "field": "/a"}
    for _ in range(9):
        deep = {"op": "not", "arg": deep}
    pack = load("rule_packs", "contract-1.0.0.json") | {"version": "1.0.1"}
    pack["rules"] = [pack["rules"][0] | {"check": deep}]
    res = client.post("/api/v1/rule-packs", json=pack, headers=headers)
    assert res.status_code == 422 and res.json()["details"][0]["reason"] == "expression_too_deep"

    unknown_table = load("rule_packs", "invoice-1.0.0.json") | {"version": "1.0.1", "reference_tables": {}}
    res = client.post("/api/v1/rule-packs", json=unknown_table, headers=headers)
    assert res.status_code == 422 and "unknown_reference_table" in {d["reason"] for d in res.json()["details"]}

    dup = load("rule_packs", "contract-1.0.0.json") | {"version": "1.0.2"}
    dup["rules"] = [dup["rules"][0], dup["rules"][0]]
    res = client.post("/api/v1/rule-packs", json=dup, headers=headers)
    assert res.status_code == 422 and res.json()["details"][0]["reason"] == "duplicate_rule_id"
