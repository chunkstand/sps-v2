"""M012 / S01 integration test: POST /api/v1/emergencies endpoint.

Proves emergency declaration with escalation-owner RBAC enforcement and 24h duration cap:

  POST /api/v1/emergencies with escalation-owner JWT
    → 201 + EmergencyResponse
    → emergency_records row persisted
    → structured log emitted

  POST with duration > 24h → 422 with error message
  POST without JWT → 401
  POST with wrong role → 403

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: API integration test against real Postgres.

## Observability Impact

Signals documented by these tests:
  - emergency_api.emergency_declared  emergency_id=... case_id=... scope=... expires_at=...
    Fires once per successful emergency declaration, before commit.
  - emergency_api.emergency_creation_failed  case_id=... reason=duration_exceeds_limit
    Fires when duration validation fails or persistence errors occur.

Diagnostic inspection:
  - SELECT emergency_id, case_id, expires_at FROM emergency_records;
  - GET /api/v1/emergencies/{emergency_id} (future endpoint)

Failure state visibility:
  - Duration > 24h → HTTP 422 + {"error": "INVALID_DURATION", "message": "..."}
  - Missing JWT → HTTP 401
  - Wrong role → HTTP 403 with role_denied error
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import EmergencyRecord, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from tests.helpers.auth_tokens import build_jwt

pytestmark = pytest.mark.integration

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    import time

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
            import time

            time.sleep(0.5)

    raise RuntimeError(
        f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    """Truncate emergency_records and permit_cases."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("TRUNCATE TABLE emergency_records, permit_cases CASCADE"))


def _seed_permit_case(case_id: str) -> None:
    """Insert minimal PermitCase row for FK satisfaction."""
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = PermitCase(
            case_id=case_id,
            tenant_id="tenant-test",
            project_id=f"project-{case_id}",
            case_state="REVIEW_PENDING",
            review_state="PENDING",
            submission_mode="DIGITAL",
            portal_support_level="FULL",
            current_release_profile="default",
        )
        session.add(row)
        session.commit()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _db_lifecycle() -> None:  # type: ignore[return]
    _wait_for_postgres_ready()
    _migrate_db()
    yield
    _reset_db()


@pytest.fixture()
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("SPS_AUTH_JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET", "test-secret-0123456789abcdef0123456789")
    monkeypatch.setenv("SPS_AUTH_JWT_ALGORITHM", "HS256")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_emergency_success(auth_env: None) -> None:
    """POST /api/v1/emergencies with escalation-owner role → 201 + persisted row."""
    asyncio.run(_run_create_emergency_success())


def test_create_emergency_duration_exceeds_24h(auth_env: None) -> None:
    """POST with duration_hours > 24 → 422 with error message."""
    asyncio.run(_run_create_emergency_duration_exceeds_24h())


def test_create_emergency_no_jwt(auth_env: None) -> None:
    """POST without JWT → 401."""
    asyncio.run(_run_create_emergency_no_jwt())


def test_create_emergency_wrong_role(auth_env: None) -> None:
    """POST with non-escalation-owner role → 403."""
    asyncio.run(_run_create_emergency_wrong_role())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_create_emergency_success() -> None:
    case_id = "CASE-EMERG-001"
    _seed_permit_case(case_id)

    token = build_jwt(subject="escalation-user-1", roles=["escalation-owner"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/emergencies/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "incident_id": "INC-001",
                "case_id": case_id,
                "scope": "high_risk",
                "allowed_bypasses": ["WORKFLOW_GUARD_SKIP"],
                "forbidden_bypasses": [],
            },
        )

    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "emergency_id" in body
    assert body["emergency_id"].startswith("EMERG-")
    assert body["case_id"] == case_id
    assert body["incident_id"] == "INC-001"
    assert body["scope"] == "high_risk"
    assert body["declared_by"] == "escalation-user-1"
    assert "expires_at" in body
    assert "cleanup_due_at" in body

    # Verify database persistence
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(EmergencyRecord, body["emergency_id"])
        assert row is not None
        assert row.case_id == case_id
        assert row.incident_id == "INC-001"
        assert row.scope == "high_risk"
        assert row.declared_by == "escalation-user-1"
        assert row.expires_at > row.started_at
        # Verify 24h max duration
        duration = row.expires_at - row.started_at
        assert duration <= dt.timedelta(hours=24)
        assert row.cleanup_due_at is not None


async def _run_create_emergency_duration_exceeds_24h() -> None:
    case_id = "CASE-EMERG-002"
    _seed_permit_case(case_id)

    token = build_jwt(subject="escalation-user-2", roles=["escalation-owner"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/emergencies/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "incident_id": "INC-002",
                "case_id": case_id,
                "scope": "high_risk",
                "allowed_bypasses": [],
                "forbidden_bypasses": [],
                "duration_hours": 25,
            },
        )

    assert response.status_code == 422, (
        f"Expected 422, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "detail" in body
    assert body["detail"]["error"] == "INVALID_DURATION"
    assert "cannot exceed 24 hours" in body["detail"]["message"]
    assert body["detail"]["requested_hours"] == 25
    assert body["detail"]["max_hours"] == 24

    # Verify no row was persisted
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        count = session.query(EmergencyRecord).filter_by(case_id=case_id).count()
        assert count == 0


async def _run_create_emergency_no_jwt() -> None:
    case_id = "CASE-EMERG-003"
    _seed_permit_case(case_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/emergencies/",
            json={
                "incident_id": "INC-003",
                "case_id": case_id,
                "scope": "high_risk",
                "allowed_bypasses": [],
                "forbidden_bypasses": [],
            },
        )

    assert response.status_code == 401
    body = response.json()
    assert "detail" in body
    assert body["detail"]["error"] == "auth_required"


async def _run_create_emergency_wrong_role() -> None:
    case_id = "CASE-EMERG-004"
    _seed_permit_case(case_id)

    # Token with wrong role (reviewer instead of escalation-owner)
    token = build_jwt(subject="reviewer-1", roles=["reviewer"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/emergencies/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "incident_id": "INC-004",
                "case_id": case_id,
                "scope": "high_risk",
                "allowed_bypasses": [],
                "forbidden_bypasses": [],
            },
        )

    assert response.status_code == 403
    body = response.json()
    assert "detail" in body
    assert body["detail"]["error_code"] == "role_denied"
    assert "escalation-owner" in body["detail"]["required_roles"]
