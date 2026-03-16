"""M009 / S03 integration tests: rollback rehearsal evidence persistence.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.

Checks:
  - POST /api/v1/releases/rollbacks/rehearsals persists evidence artifact rows.
  - Evidence registry GET returns stored metadata.
  - Checksum mismatches are rejected with structured errors.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import sps.api.routes.releases as releases
from sps.api.main import app
from sps.config import get_settings
from sps.db.models import EvidenceArtifact
from sps.db.session import get_engine, get_sessionmaker


if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal/Postgres integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    engine = get_engine()

    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError(
        f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("TRUNCATE TABLE evidence_artifacts CASCADE"))


def _canonical_payload_bytes(payload: dict) -> bytes:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return payload_json.encode("utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _db_lifecycle() -> None:  # type: ignore[return]
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()
    yield
    _reset_db()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_rollback_rehearsal_persists_evidence_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()

    log_calls: list[str] = []

    def _info(msg: str, *_args, **_kwargs) -> None:
        log_calls.append(msg)

    monkeypatch.setattr(releases.logger, "info", _info)

    release_id = "REL-ROLLBACK-001"
    rehearsal_id = "REHEARSAL-001"
    payload = {
        "status": "SUCCESS",
        "duration_seconds": 84,
        "rollback_version": "v2026.03.16",
    }
    payload_bytes = _canonical_payload_bytes(payload)
    checksum = f"sha256:{hashlib.sha256(payload_bytes).hexdigest()}"

    request_body = {
        "release_id": release_id,
        "rehearsal_id": rehearsal_id,
        "environment": "staging",
        "operator_id": "ops-001",
        "authoritativeness": "INFORMATIONAL",
        "artifact_class": "ROLLBACK_REHEARSAL",
        "checksum": checksum,
        "evidence_payload": payload,
        "notes": "nightly rehearsal",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/releases/rollbacks/rehearsals",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json=request_body,
        )

    assert response.status_code == 201, (
        "Expected 201 from POST /api/v1/releases/rollbacks/rehearsals, "
        f"got {response.status_code}: {response.text}"
    )

    payload_response = response.json()
    artifact_id = payload_response["artifact_id"]
    assert payload_response["artifact_class"] == "ROLLBACK_REHEARSAL"
    assert payload_response["retention_class"] == "RELEASE_EVIDENCE"
    assert payload_response["checksum"] == checksum
    assert any(
        "rollback_rehearsal.created" in entry for entry in log_calls
    ), "Expected rollback rehearsal creation log"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        evidence_resp = await client.get(f"/api/v1/evidence/artifacts/{artifact_id}")

    assert evidence_resp.status_code == 200, evidence_resp.text
    evidence_payload = evidence_resp.json()
    assert evidence_payload["artifact_id"] == artifact_id
    assert evidence_payload["artifact_class"] == "ROLLBACK_REHEARSAL"
    assert evidence_payload["retention_class"] == "RELEASE_EVIDENCE"
    assert evidence_payload["linked_object_id"] == release_id
    assert evidence_payload["checksum"] == checksum

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(EvidenceArtifact, artifact_id)
        assert row is not None, "Evidence artifact row not found"
        assert row.artifact_class == "ROLLBACK_REHEARSAL"
        assert row.retention_class == "RELEASE_EVIDENCE"
        assert row.created_at <= _utcnow()


@pytest.mark.anyio
async def test_rollback_rehearsal_failure_rejects_checksum_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()

    log_calls: list[str] = []

    def _warning(msg: str, *_args, **_kwargs) -> None:
        log_calls.append(msg)

    monkeypatch.setattr(releases.logger, "warning", _warning)

    payload = {"status": "FAIL"}
    payload_bytes = _canonical_payload_bytes(payload)
    _ = hashlib.sha256(payload_bytes).hexdigest()

    bad_checksum = f"sha256:{'0' * 64}"
    request_body = {
        "release_id": "REL-ROLLBACK-FAIL",
        "rehearsal_id": "REHEARSAL-FAIL",
        "environment": "staging",
        "operator_id": "ops-002",
        "authoritativeness": "INFORMATIONAL",
        "artifact_class": "ROLLBACK_REHEARSAL",
        "checksum": bad_checksum,
        "evidence_payload": payload,
        "notes": "bad checksum",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/releases/rollbacks/rehearsals",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json=request_body,
        )

    assert response.status_code == 422, (
        "Expected 422 from checksum mismatch, "
        f"got {response.status_code}: {response.text}"
    )
    payload_response = response.json()
    assert payload_response["detail"]["error"] == "checksum_mismatch"
    assert payload_response["detail"]["expected"] == bad_checksum
    assert any(
        "rollback_rehearsal.checksum_mismatch" in entry for entry in log_calls
    ), "Expected checksum mismatch log"
