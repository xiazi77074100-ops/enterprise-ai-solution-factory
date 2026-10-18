import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "env": "test",
        "database_url": os.environ.get("EASF_TEST_DATABASE_URL", "postgresql+psycopg://unused@127.0.0.1:1/unused"),
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(make_settings()), raise_server_exceptions=False)


@pytest.fixture
def db_url() -> str:
    url = os.environ.get("EASF_TEST_DATABASE_URL")
    if not url:
        pytest.skip("EASF_TEST_DATABASE_URL is not set")
    return url


@pytest.fixture
def migration_url() -> str:
    url = os.environ.get("EASF_MIGRATION_DATABASE_URL")
    if not url:
        pytest.skip("EASF_MIGRATION_DATABASE_URL is not set")
    return url
