"""VA-001 (self-assessment 2026-10-18): production must not run with a non-Secure session cookie."""

import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_prod_without_secure_cookie_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="EASF_COOKIE_SECURE"):
        make_settings(env="prod", cookie_secure=False)


def test_prod_with_secure_cookie_uses_host_prefix() -> None:
    settings = make_settings(env="prod", cookie_secure=True)
    assert settings.session_cookie_name == "__Host-easf_session"
