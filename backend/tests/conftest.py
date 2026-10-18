import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.main import create_app


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "env": "test",
        "database_url": os.environ.get("EASF_TEST_DATABASE_URL", "postgresql+psycopg://unused@127.0.0.1:1/unused"),
        "secret_key": "test-secret-key-0123456789-abcdefghijklmnop",
        "site_origin": "http://testserver",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(make_settings()), raise_server_exceptions=False)


def _test_database_url(name: str) -> str:
    url = os.environ.get(name)
    if not url:
        pytest.skip(f"{name} is not set")
    # Tests truncate and downgrade the schema: refuse anything but a dedicated *_test database (P2-00).
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.exit(f"{name} must point to a database whose name ends with _test (got {database!r})", returncode=2)
    return url


@pytest.fixture(scope="session")
def db_url() -> str:
    return _test_database_url("EASF_TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def migration_url() -> str:
    """Owner role on the test database (passed to alembic as EASF_MIGRATION_DATABASE_URL)."""
    return _test_database_url("EASF_TEST_MIGRATION_DATABASE_URL")
