"""M009 / S01 integration test: ops dashboard metrics endpoint.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.

Checks:
  - /api/v1/ops/dashboard/metrics returns expected counts and timestamps.
"""

from __future__ import annotations

import datetime as dt
import os
import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import ContradictionArtifact, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.services.ops_metrics import STALLED_REVIEW_THRESHOLD


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
        conn.execute(sa.text("TRUNCATE TABLE contradiction_artifacts, permit_cases CASCADE"))


def _seed_case(
    *,
    case_id: str,
    case_state: str,
    updated_at: dt.datetime,
) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-test",
                project_id=f"PROJ-{case_id}",
                case_state=case_state,
                review_state="PENDING",
                submission_mode="PORTAL",
                portal_support_level="FULL",
                current_package_id=None,
                current_release_profile="default",
                legal_hold=False,
                closure_reason=None,
                created_at=updated_at,
                updated_at=updated_at,
            )
        )
        session.commit()


def _seed_contradiction(
    *,
    contradiction_id: str,
    case_id: str,
    resolution_status: str,
    blocking_effect: bool,
) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            ContradictionArtifact(
                contradiction_id=contradiction_id,
                case_id=case_id,
                scope="REQUIREMENTS",
                source_a="source-a",
                source_b="source-b",
                ranking_relation="SAME_RANK",
                blocking_effect=blocking_effect,
                resolution_status=resolution_status,
                resolved_at=_utcnow() if resolution_status != "OPEN" else None,
                resolved_by="reviewer-ops" if resolution_status != "OPEN" else None,
                created_at=_utcnow(),
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ops_dashboard_page_renders() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ops")
        static_response = await client.get("/static/ops.js")

    assert response.status_code == 200, (
        f"Expected 200 from /ops, got {response.status_code}: {response.text}"
    )
    assert "Queue Health" in response.text
    assert "Legacy API Key" in response.text
    assert "This page renders without protected data." in response.text
    assert "/static/ops.js" in response.text
    assert 'data-metrics-endpoint="/api/v1/ops/dashboard/metrics"' in response.text

    assert static_response.status_code == 200
    assert "/api/v1/ops/dashboard/metrics" in static_response.text
    assert "metrics_fetch_failed" in static_response.text
    assert "X-Reviewer-Api-Key" in static_response.text
    assert "legacy/manual reviewer key" in static_response.text


@pytest.mark.anyio
async def test_ops_metrics_endpoint_returns_expected_counts() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    now = _utcnow()
    stalled_at = now - STALLED_REVIEW_THRESHOLD - dt.timedelta(hours=1)

    _seed_case(case_id="CASE-QUEUE-1", case_state="REVIEW_PENDING", updated_at=now)
    _seed_case(case_id="CASE-QUEUE-2", case_state="REVIEW_PENDING", updated_at=stalled_at)
    _seed_case(case_id="CASE-OTHER", case_state="INTAKE_PENDING", updated_at=now)

    _seed_contradiction(
        contradiction_id="CONTRA-OPEN-BLOCKING",
        case_id="CASE-QUEUE-1",
        resolution_status="OPEN",
        blocking_effect=True,
    )
    _seed_contradiction(
        contradiction_id="CONTRA-OPEN-NONBLOCK",
        case_id="CASE-QUEUE-1",
        resolution_status="OPEN",
        blocking_effect=False,
    )
    _seed_contradiction(
        contradiction_id="CONTRA-RESOLVED",
        case_id="CASE-QUEUE-2",
        resolution_status="RESOLVED",
        blocking_effect=True,
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/ops/dashboard/metrics",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
        )

    assert response.status_code == 200, (
        f"Expected 200 from ops metrics, got {response.status_code}: {response.text}"
    )

    payload = response.json()
    assert payload["queue_depth"] == 2
    assert payload["contradiction_backlog"] == 1
    assert payload["stalled_review_count"] == 1

    generated_at = dt.datetime.fromisoformat(payload["generated_at"])
    stalled_before = dt.datetime.fromisoformat(payload["stalled_review_before"])
    delta = generated_at - stalled_before
    assert payload["stalled_review_threshold_hours"] == int(
        STALLED_REVIEW_THRESHOLD.total_seconds() // 3600
    )
    assert abs(delta.total_seconds() - STALLED_REVIEW_THRESHOLD.total_seconds()) <= 2
