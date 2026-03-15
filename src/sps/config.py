from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _redact_url_password(url: str) -> str:
    """Best-effort password redaction for DSN-like URLs.

    Never log raw DSNs that may contain passwords.
    """

    try:
        parts = urlsplit(url)
        if parts.username is None:
            return url

        # Rebuild netloc without password.
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        user = parts.username
        netloc = f"{user}:***@{host}{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        # If parsing fails, return something safe.
        return "<redacted>"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    env: str = Field(default="local", validation_alias="SPS_ENV")

    # Postgres
    db_host: str = Field(default="localhost", validation_alias="SPS_DB_HOST")
    db_port: int = Field(default=5432, validation_alias="SPS_DB_PORT")
    db_name: str = Field(default="sps", validation_alias="SPS_DB_NAME")
    db_user: str = Field(default="sps", validation_alias="SPS_DB_USER")
    db_password: str = Field(default="sps", validation_alias="SPS_DB_PASSWORD")

    # Prefer explicit DSN when present.
    db_dsn: str | None = Field(default=None, validation_alias="SPS_DB_DSN")

    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", validation_alias="SPS_LOG_LEVEL"
    )

    def postgres_dsn(self) -> str:
        if self.db_dsn:
            return self.db_dsn
        # SQLAlchemy URL form for psycopg 3
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def redacted_postgres_dsn(self) -> str:
        return _redact_url_password(self.postgres_dsn())


@lru_cache
def get_settings() -> Settings:
    # Cached for process lifetime; tests can clear via get_settings.cache_clear().
    return Settings()
