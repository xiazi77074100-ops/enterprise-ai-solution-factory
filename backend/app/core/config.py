"""Settings from environment variables (prefix EASF_). Secrets are SecretStr and never logged."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EASF_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "assessment", "prod"] = "dev"
    database_url: SecretStr = Field(description="Application role (DML only).")
    site_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    hsts_enabled: bool = False
    max_request_bytes: int = Field(default=1_048_576, ge=1024, le=20_971_520)

    @property
    def expose_docs(self) -> bool:
        # OpenAPI/docs are served only in dev; elsewhere contracts/openapi.yaml is the contract.
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
