"""Real PostgreSQL (ADR-004): readiness, migrations up/down, application role has no DDL."""

import os
import subprocess  # nosec B404 - fixed alembic command, no user input
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from app.main import create_app
from tests.conftest import make_settings

BACKEND = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.db


def alembic(*args: str, migration_url: str) -> None:
    env = {**os.environ, "EASF_MIGRATION_DATABASE_URL": migration_url}
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, check=True)  # noqa: S603  # nosec B603


def test_migrations_upgrade_downgrade_upgrade(migration_url: str) -> None:
    alembic("upgrade", "head", migration_url=migration_url)
    alembic("downgrade", "base", migration_url=migration_url)
    alembic("upgrade", "head", migration_url=migration_url)


def test_ready_with_real_database(db_url: str) -> None:
    res = TestClient(create_app(make_settings(database_url=db_url))).get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ready_reports_503_when_database_unreachable() -> None:
    unreachable = "postgresql+psycopg://nobody:x@127.0.0.1:1/none?connect_timeout=1"
    app = create_app(make_settings(database_url=unreachable))
    res = TestClient(app, raise_server_exceptions=False).get("/ready")
    assert res.status_code == 503
    assert res.json()["code"] == "service_unavailable"
    assert "nobody" not in res.text


def test_application_role_cannot_run_ddl(db_url: str) -> None:
    with create_engine(db_url).connect() as conn, pytest.raises(ProgrammingError):
        conn.execute(text("CREATE TABLE should_fail (id int)"))
