"""Auth, CSRF/Origin, object-level authorization (jp-vuln-assessment checklist B, C, D) on real PostgreSQL."""

import os
import subprocess  # nosec B404 - fixed alembic command
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import Session

from app.auth.models import User, UserSession
from app.core.db import make_session_factory
from app.core.security import hash_password
from app.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.db
BACKEND = Path(__file__).resolve().parents[2]
ORIGIN = {"Origin": "http://testserver"}
PASSWORD = "correct horse battery staple"
TABLES = (
    "solution",
    "capability_version",
    "rule_pack_version",
    "requirement_revision",
    "project_member",
    "project",
    "user_session",
    "app_user",
)


@pytest.fixture(scope="module")
def migrated(migration_url: str, db_url: str) -> None:
    env = {**os.environ, "EASF_MIGRATION_DATABASE_URL": migration_url}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)  # noqa: S603  # nosec B603


@pytest.fixture
def db(migrated: None, db_url: str, migration_url: str) -> Iterator[Session]:
    # The owner role truncates (versioned rows are immutable: DELETE is rejected by trigger).
    with create_engine(migration_url).begin() as owner:
        owner.execute(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))  # nosec B608 - fixed table names
    with make_session_factory(make_settings(database_url=db_url))() as session:
        yield session


@pytest.fixture
def app_client(db: Session, db_url: str) -> TestClient:
    return TestClient(create_app(make_settings(database_url=db_url)), raise_server_exceptions=False)


def new_client(db_url: str) -> TestClient:
    return TestClient(create_app(make_settings(database_url=db_url)), raise_server_exceptions=False)


def make_user(db: Session, login_id: str, admin: bool = False) -> User:
    user = User(
        login_id=login_id, display_name=f"{login_id} 太郎", password_hash=hash_password(PASSWORD), is_admin=admin
    )
    db.add(user)
    db.commit()
    return user


def login(client: TestClient, login_id: str, password: str = PASSWORD) -> dict[str, str]:
    res = client.post("/api/v1/session", json={"login_id": login_id, "password": password}, headers=ORIGIN)
    assert res.status_code == 200, res.text
    return {**ORIGIN, "X-CSRF-Token": res.json()["csrf_token"]}


def create_project(client: TestClient, headers: dict[str, str], name: str = "請求書 POC") -> str:
    res = client.post("/api/v1/projects", json={"name": name, "business_domain": "経理"}, headers=headers)
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


# --- B: authentication and session ---------------------------------------------------------------


def test_login_sets_httponly_cookie_and_rotates_session(app_client: TestClient, db: Session) -> None:
    make_user(db, "alice")
    login(app_client, "alice")
    first = app_client.cookies.get("easf_session")
    login(app_client, "alice")
    second = app_client.cookies.get("easf_session")
    assert first and second and first != second
    res = app_client.post("/api/v1/session", json={"login_id": "alice", "password": PASSWORD}, headers=ORIGIN)
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert db.query(UserSession).count() == 1  # old ids were removed on each login


def test_login_failure_is_identical_for_unknown_user_and_wrong_password(app_client: TestClient, db: Session) -> None:
    make_user(db, "alice")
    unknown = app_client.post("/api/v1/session", json={"login_id": "nobody", "password": "x"}, headers=ORIGIN)
    wrong = app_client.post("/api/v1/session", json={"login_id": "alice", "password": "x"}, headers=ORIGIN)
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["message"] == wrong.json()["message"]
    assert unknown.json()["code"] == wrong.json()["code"] == "login_failed"


def test_lockout_after_repeated_failures(app_client: TestClient, db: Session) -> None:
    make_user(db, "alice")
    for _ in range(5):
        app_client.post("/api/v1/session", json={"login_id": "alice", "password": "wrong"}, headers=ORIGIN)
    locked = app_client.post("/api/v1/session", json={"login_id": "alice", "password": PASSWORD}, headers=ORIGIN)
    assert locked.status_code == 401
    assert locked.json()["code"] == "login_failed"


def test_login_requires_same_origin(app_client: TestClient, db: Session) -> None:
    make_user(db, "alice")
    for headers in ({}, {"Origin": "https://evil.example"}):
        res = app_client.post("/api/v1/session", json={"login_id": "alice", "password": PASSWORD}, headers=headers)
        assert res.status_code == 403


def test_logout_invalidates_server_side_session(app_client: TestClient, db: Session, db_url: str) -> None:
    make_user(db, "alice")
    headers = login(app_client, "alice")
    stolen = app_client.cookies.get("easf_session")
    assert app_client.delete("/api/v1/session", headers=headers).status_code == 204
    replay = new_client(db_url)
    replay.cookies.set("easf_session", stolen or "")
    assert replay.get("/api/v1/session").status_code == 401


def test_idle_session_expires(app_client: TestClient, db: Session) -> None:
    make_user(db, "alice")
    login(app_client, "alice")
    db.execute(update(UserSession).values(last_seen_at=datetime.now(UTC) - timedelta(minutes=31)))
    db.commit()
    assert app_client.get("/api/v1/session").status_code == 401


def test_unauthenticated_requests_are_rejected(app_client: TestClient, db: Session) -> None:
    for method, path in (("GET", "/api/v1/projects"), ("GET", "/api/v1/session"), ("POST", "/api/v1/projects")):
        res = app_client.request(method, path, json={} if method == "POST" else None, headers=ORIGIN)
        assert res.status_code == 401, (method, path)


# --- D: CSRF / Origin ------------------------------------------------------------------------------


def test_state_change_requires_csrf_token_and_origin(app_client: TestClient, db: Session) -> None:
    make_user(db, "admin", admin=True)
    headers = login(app_client, "admin")
    body = {"name": "x", "business_domain": "y"}
    assert app_client.post("/api/v1/projects", json=body, headers=ORIGIN).status_code == 403
    bad_token = {**headers, "X-CSRF-Token": "0" * 64}
    assert app_client.post("/api/v1/projects", json=body, headers=bad_token).status_code == 403
    other_origin = {**headers, "Origin": "https://evil.example"}
    assert app_client.post("/api/v1/projects", json=body, headers=other_origin).status_code == 403
    assert app_client.post("/api/v1/projects", json=body, headers=headers).status_code == 201


# --- C: authorization ------------------------------------------------------------------------------


def test_only_admin_or_lead_can_create_projects(app_client: TestClient, db: Session) -> None:
    make_user(db, "bob")
    headers = login(app_client, "bob")
    res = app_client.post("/api/v1/projects", json={"name": "x", "business_domain": "y"}, headers=headers)
    assert res.status_code == 403


def test_project_of_another_user_is_not_found(app_client: TestClient, db: Session, db_url: str) -> None:
    make_user(db, "admin", admin=True)
    make_user(db, "bob")
    project_id = create_project(app_client, login(app_client, "admin"))
    other = new_client(db_url)
    login(other, "bob")
    for path in (
        f"/api/v1/projects/{project_id}",
        f"/api/v1/projects/{project_id}/members",
        f"/api/v1/projects/{project_id}/requirements",
        f"/api/v1/projects/{uuid.uuid4()}",
    ):
        assert other.get(path).status_code == 404, path
    assert other.get("/api/v1/projects").json()["page"]["total"] == 0


def test_mass_assignment_fields_are_rejected(app_client: TestClient, db: Session) -> None:
    make_user(db, "admin", admin=True)
    headers = login(app_client, "admin")
    body = {"name": "x", "business_domain": "y", "owner_id": str(uuid.uuid4())}
    res = app_client.post("/api/v1/projects", json=body, headers=headers)
    assert res.status_code == 422
    assert str(body["owner_id"]) not in res.text


def test_list_sort_allowlist_and_like_escape(app_client: TestClient, db: Session) -> None:
    make_user(db, "admin", admin=True)
    headers = login(app_client, "admin")
    create_project(app_client, headers, "100% 達成")
    create_project(app_client, headers, "別件")
    assert app_client.get("/api/v1/projects", params={"sort": "name; DROP TABLE project"}).status_code == 422
    assert app_client.get("/api/v1/projects", params={"q": "%"}).json()["page"]["total"] == 1
    assert app_client.get("/api/v1/projects", params={"q": "_"}).json()["page"]["total"] == 0
    page = app_client.get("/api/v1/projects", params={"limit": 1}).json()
    assert page["page"]["total"] == 2 and page["page"]["next_cursor"]
    assert app_client.get("/api/v1/projects", params={"cursor": "not-a-cursor"}).status_code == 422


def test_members_rules_and_access(app_client: TestClient, db: Session, db_url: str) -> None:
    admin = make_user(db, "admin", admin=True)
    bob = make_user(db, "bob")
    headers = login(app_client, "admin")
    project_id = create_project(app_client, headers)
    url = f"/api/v1/projects/{project_id}/members"
    drop_self = [{"user_id": str(bob.id), "roles": ["solution_lead"]}]
    assert app_client.put(url, json=drop_self, headers=headers).status_code == 422
    unknown = [
        {"user_id": str(admin.id), "roles": ["solution_lead"]},
        {"user_id": str(uuid.uuid4()), "roles": ["qa_evaluator"]},
    ]
    assert app_client.put(url, json=unknown, headers=headers).status_code == 422
    bad_role = [{"user_id": str(admin.id), "roles": ["solution_lead", "admin"]}]
    assert app_client.put(url, json=bad_role, headers=headers).status_code == 422
    ok = [
        {"user_id": str(admin.id), "roles": ["solution_lead"]},
        {"user_id": str(bob.id), "roles": ["business_reviewer"]},
    ]
    assert app_client.put(url, json=ok, headers=headers).status_code == 200
    reviewer = new_client(db_url)
    reviewer_headers = login(reviewer, "bob")
    assert reviewer.get(f"/api/v1/projects/{project_id}").status_code == 200
    assert reviewer.put(url, json=ok, headers=reviewer_headers).status_code == 403
    req = {"content": "請求書の項目を抽出する"}
    assert (
        reviewer.post(f"/api/v1/projects/{project_id}/requirements", json=req, headers=reviewer_headers).status_code
        == 403
    )


def test_requirement_revision_approval_rules(app_client: TestClient, db: Session, db_url: str) -> None:
    admin = make_user(db, "admin", admin=True)
    carol = make_user(db, "carol")
    headers = login(app_client, "admin")
    project_id = create_project(app_client, headers)
    members = [
        {"user_id": str(admin.id), "roles": ["solution_lead"]},
        {"user_id": str(carol.id), "roles": ["solution_lead"]},
    ]
    app_client.put(f"/api/v1/projects/{project_id}/members", json=members, headers=headers)
    first = app_client.post(f"/api/v1/projects/{project_id}/requirements", json={"content": "初版"}, headers=headers)
    second = app_client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"content": "第 2 版"}, headers=headers
    )
    assert (first.json()["revision"], second.json()["revision"]) == (1, 2)
    revision_id = second.json()["id"]
    assert app_client.post(f"/api/v1/requirements/{revision_id}/approve", headers=headers).status_code == 403
    lead = new_client(db_url)
    lead_headers = login(lead, "carol")
    approved = lead.post(f"/api/v1/requirements/{revision_id}/approve", headers=lead_headers)
    assert approved.status_code == 200 and approved.json()["approved_by"] == str(carol.id)
    assert lead.post(f"/api/v1/requirements/{revision_id}/approve", headers=lead_headers).status_code == 409
    listed = lead.get(f"/api/v1/projects/{project_id}/requirements").json()
    assert [r["revision"] for r in listed] == [2, 1]
