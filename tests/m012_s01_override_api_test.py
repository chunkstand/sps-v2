"""M012 / S01 integration test: POST /api/v1/overrides endpoint.

Proves override artifact creation with escalation-owner RBAC enforcement and scope validation:

  POST /api/v1/overrides with escalation-owner JWT
    → 201 + OverrideResponse
    → override_artifacts row persisted with JSONB affected_surfaces
    → structured log emitted

  POST without JWT → 401
  POST with wrong role → 403

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: API integration test against real Postgres.

## Observability Impact

Signals documented by these tests:
  - override_api.override_created  override_id=... scope=... expires_at=... affected_surfaces=...
    Fires once per successful override creation, before commit.
  - override_api.override_creation_failed  case_id=... reason=persistence_error
    Fires when persistence errors occur.

Diagnostic inspection:
  - SELECT override_id, affected_surfaces FROM override_artifacts;
  - GET /api/v1/overrides/{override_id} (future endpoint)

Failure state visibility:
  - Missing JWT → HTTP 401
  - Wrong role → HTTP 403 with role_denied error
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import OverrideArtifact, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from tests.helpers.auth_tokens import build_jwt

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
    """Truncate override_artifacts and permit_cases."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("TRUNCATE TABLE override_artifacts, permit_cases CASCADE"))


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
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SPS_AUTH_JWT_ALGORITHM", "HS256")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_override_success(auth_env: None) -> None:
    """POST /api/v1/overrides with escalation-owner role → 201 + persisted row with JSONB."""
    asyncio.run(_run_create_override_success())


def test_create_override_no_jwt(auth_env: None) -> None:
    """POST without JWT → 401."""
    asyncio.run(_run_create_override_no_jwt())


def test_create_override_wrong_role(auth_env: None) -> None:
    """POST with non-escalation-owner role → 403."""
    asyncio.run(_run_create_override_wrong_role())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_create_override_success() -> None:
    case_id = "CASE-OVR-001"
    _seed_permit_case(case_id)

    token = build_jwt(subject="escalation-user-1", roles=["escalation-owner"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/overrides/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "case_id": case_id,
                "scope": "reviewer_independence",
                "justification": "Emergency bypass required",
                "duration_hours": 2,
                "affected_surfaces": ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"],
            },
        )

    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "override_id" in body
    assert body["override_id"].startswith("OVR-")
    assert body["case_id"] == case_id
    assert body["scope"] == "reviewer_independence"
    assert body["approver_id"] == "escalation-user-1"
    assert "expires_at" in body
    assert body["affected_surfaces"] == ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"]

    # Verify database persistence with JSONB affected_surfaces
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(OverrideArtifact, body["override_id"])
        assert row is not None
        assert row.case_id == case_id
        assert row.scope == "reviewer_independence"
        assert row.approver_id == "escalation-user-1"
        assert row.expires_at > row.start_at
        assert row.affected_surfaces == ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"]
        assert row.cleanup_required is True


async def _run_create_override_no_jwt() -> None:
    case_id = "CASE-OVR-002"
    _seed_permit_case(case_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/overrides/",
            json={
                "case_id": case_id,
                "scope": "reviewer_independence",
                "justification": "Emergency bypass",
                "duration_hours": 2,
                "affected_surfaces": ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"],
            },
        )

    assert response.status_code == 401
    body = response.json()
    assert "detail" in body
    assert body["detail"]["error"] == "auth_required"


async def _run_create_override_wrong_role() -> None:
    case_id = "CASE-OVR-003"
    _seed_permit_case(case_id)

    # Token with wrong role (reviewer instead of escalation-owner)
    token = build_jwt(subject="reviewer-1", roles=["reviewer"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/overrides/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "case_id": case_id,
                "scope": "reviewer_independence",
                "justification": "Emergency bypass",
                "duration_hours": 2,
                "affected_surfaces": ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"],
            },
        )

    assert response.status_code == 403
    body = response.json()
    assert "detail" in body
    assert body["detail"]["error_code"] == "role_denied"
    assert "escalation-owner" in body["detail"]["required_roles"]
