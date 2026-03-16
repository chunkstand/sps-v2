from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import AliasChoices, Field
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

    # Temporal (local dev default matches docker-compose)
    temporal_address: str = Field(
        default="localhost:7233",
        validation_alias=AliasChoices("SPS_TEMPORAL_ADDRESS", "TEMPORAL_ADDRESS"),
    )
    temporal_namespace: str = Field(
        default="default",
        validation_alias=AliasChoices("SPS_TEMPORAL_NAMESPACE", "TEMPORAL_NAMESPACE"),
    )
    temporal_task_queue: str = Field(
        default="sps-permit-case",
        validation_alias=AliasChoices("SPS_TEMPORAL_TASK_QUEUE", "TEMPORAL_TASK_QUEUE"),
    )

    # S3-compatible object storage (MinIO in local dev)
    s3_endpoint_url: str = Field(default="http://localhost:9000", validation_alias="SPS_S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="minio", validation_alias="SPS_S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minio123", validation_alias="SPS_S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", validation_alias="SPS_S3_REGION")

    s3_bucket_evidence: str = Field(default="sps-evidence", validation_alias="SPS_S3_BUCKET_EVIDENCE")
    s3_bucket_release: str = Field(default="sps-release", validation_alias="SPS_S3_BUCKET_RELEASE")

    s3_presign_expires_seconds: int = Field(default=600, validation_alias="SPS_S3_PRESIGN_EXPIRES_SECONDS")

    # Reviewer API
    # IMPORTANT: this value must never be logged — treat it as a credential.
    reviewer_api_key: str = Field(default="dev-reviewer-key", validation_alias="SPS_REVIEWER_API_KEY")

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
