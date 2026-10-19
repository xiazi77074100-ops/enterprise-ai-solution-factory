"""Settings from environment variables (prefix EASF_). Secrets are SecretStr and never logged."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EASF_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "assessment", "prod"] = "dev"
    database_url: SecretStr = Field(description="Application role (DML only).")
    site_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    hsts_enabled: bool = False
    max_request_bytes: int = Field(default=1_048_576, ge=1024, le=20_971_520)
    secret_key: SecretStr = Field(min_length=32, description="HMAC key for CSRF tokens.")
    session_idle_minutes: int = Field(default=30, ge=1, le=1440)
    session_absolute_hours: int = Field(default=8, ge=1, le=72)
    login_max_failures: int = Field(default=5, ge=1, le=20)
    login_lock_minutes: int = Field(default=15, ge=1, le=1440)
    storage_dir: Path = Field(default=Path("var/documents"), description="Uploaded documents (never served).")

    @model_validator(mode="after")
    def _prod_requires_secure_cookie(self) -> "Settings":
        # VA-001: production must never fall back to a non-Secure session cookie.
        if self.env == "prod" and not self.cookie_secure:
            raise ValueError("EASF_COOKIE_SECURE must be true when EASF_ENV=prod")
        return self

    @property
    def session_cookie_name(self) -> str:
        # __Host- requires Secure; plain HTTP is allowed only for local dev (ADR-006).
        return "__Host-easf_session" if self.cookie_secure else "easf_session"

    @property
    def expose_docs(self) -> bool:
        # OpenAPI/docs are served only in dev; elsewhere contracts/openapi.yaml is the contract.
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
