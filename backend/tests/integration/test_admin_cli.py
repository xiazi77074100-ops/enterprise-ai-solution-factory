"""Admin CLI creates and deactivates users; passwords never come from argv."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import admin
from app.auth.models import User
from app.core import config
from tests.integration.test_auth_projects import db, migrated  # noqa: F401  # reuse fixtures

pytestmark = pytest.mark.db


def test_create_and_deactivate_user(db: Session, monkeypatch: pytest.MonkeyPatch, db_url: str) -> None:  # noqa: F811
    monkeypatch.setenv("EASF_DATABASE_URL", db_url)
    monkeypatch.setenv("EASF_SECRET_KEY", "test-secret-key-0123456789-abcdefghijklmnop")
    monkeypatch.setenv("EASF_NEW_USER_PASSWORD", "a-long-enough-password")
    config.get_settings.cache_clear()
    assert admin.main(["create-user", "--login-id", "dave", "--display-name", "田中 大輔", "--admin"]) == 0
    assert admin.main(["create-user", "--login-id", "dave", "--display-name", "dup"]) == 1
    user = db.execute(select(User).where(User.login_id == "dave")).scalar_one()
    assert user.is_admin and user.is_active and user.password_hash.startswith("$argon2id$")
    assert admin.main(["deactivate-user", "--login-id", "dave"]) == 0
    db.refresh(user)
    assert not user.is_active
    monkeypatch.setenv("EASF_NEW_USER_PASSWORD", "short")
    assert admin.main(["create-user", "--login-id", "erin", "--display-name", "x"]) == 1
    config.get_settings.cache_clear()
