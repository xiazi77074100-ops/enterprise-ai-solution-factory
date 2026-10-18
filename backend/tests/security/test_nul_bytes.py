"""VA-004 (self-assessment 2026-10-18, ZAP): NUL characters must be rejected with 422, not reach PostgreSQL (500)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_auth_projects import (  # noqa: F401  # shared fixtures
    ORIGIN,
    PASSWORD,
    db,
    make_user,
    migrated,
    new_client,
)


def test_nul_in_query_string_is_rejected(client: TestClient) -> None:
    res = client.get("/api/v1/projects?q=a%00b")
    assert res.status_code == 422
    assert res.json()["code"] == "validation_error"


def test_nul_in_path_is_rejected(client: TestClient) -> None:
    res = client.get("/api/v1/capabilities/a%00b/versions/1.0.0")
    assert res.status_code == 422


@pytest.mark.db
def test_nul_in_json_body_is_rejected_before_the_database(db: Session, db_url: str) -> None:  # noqa: F811
    make_user(db, "admin", admin=True)
    client = new_client(db_url)
    login = client.post("/api/v1/session", json={"login_id": "admin", "password": PASSWORD}, headers=ORIGIN)
    headers = {**ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}

    bad = client.post("/api/v1/projects", json={"name": "a\x00b", "business_domain": "経理"}, headers=headers)
    assert bad.status_code == 422
    assert bad.json()["code"] == "validation_error"

    # A literal backslash followed by "u0000" is ordinary text, not a NUL character.
    ok = client.post("/api/v1/projects", json={"name": "a\\u0000b", "business_domain": "経理"}, headers=headers)
    assert ok.status_code == 201
    assert ok.json()["name"] == "a\\u0000b"
