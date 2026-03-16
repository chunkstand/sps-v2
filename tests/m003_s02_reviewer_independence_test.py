"""M003 / S02 integration tests: Reviewer independence policy guard.

Proves the independence guard on POST /api/v1/reviews/decisions:

  1. Self-approval (reviewer_id == subject_author_id) → 403
       - body: error=REVIEW_INDEPENDENCE_DENIED, guard_assertion_id=INV-SPS-REV-001,
               normalized_business_invariants=["INV-008"]
       - no review_decisions row written to Postgres

  2. Distinct reviewer (reviewer_id != subject_author_id) → 201
       - review_decisions row written with reviewer_independence_status="PASS"
       - signal delivery failure (no Temporal worker) is expected and swallowed; 201 still returned

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: mirrors m003_s01 (real Postgres, no Temporal worker needed — guard fires before INSERT).

## Observability Impact

Signals added/changed by this task:
  - WARNING log line: `reviewer_api.independence_denied reviewer_id=... subject_author_id=... guard_assertion_id=INV-SPS-REV-001`
    emitted by _check_reviewer_independence() before any DB operation on denial path.
  - 403 response body shape: {"detail": {"error": "REVIEW_INDEPENDENCE_DENIED",
    "guard_assertion_id": "INV-SPS-REV-001", "normalized_business_invariants": ["INV-008"]}}

Diagnostic inspection:
  - Denial attempts: `docker compose logs api | grep independence_denied`
  - DB state: `SELECT decision_id, reviewer_independence_status FROM review_decisions WHERE case_id = '...';`
    → no row on denial; PASS on success

Failure state visibility:
  - 403 body contains stable `guard_assertion_id` and `normalized_business_invariants` for cross-system correlation
  - Denial log includes both `reviewer_id` and `subject_author_id` for audit
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers (inlined — self-contained, no coupling to S01 test module)
# ---------------------------------------------------------------------------


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
        conn.execute(
            sa.text(
                "TRUNCATE TABLE case_transition_ledger, review_decisions, permit_cases CASCADE"
            )
        )


def _seed_permit_case(case_id: str) -> None:
    """Insert a minimal PermitCase row so review_decisions FK constraint is satisfied.

    The independence guard fires before the INSERT; the success test still needs
    the parent row to exist so the DB commit doesn't raise a FK violation.
    """
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
# Tests
# ---------------------------------------------------------------------------


def test_independence_self_approval_denied_403() -> None:
    """Self-approval (reviewer_id == subject_author_id) → 403 + no DB row."""
    asyncio.run(_run_self_approval_denied_test())


def test_independence_distinct_reviewer_succeeds_201() -> None:
    """Distinct reviewer → 201 + reviewer_independence_status=PASS in DB."""
    asyncio.run(_run_distinct_reviewer_test())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_self_approval_denied_test() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-SELF-APPROVAL-001"
    decision_id = "DEC-SELF-APPROVAL-001"
    idempotency_key = "idem/self-approval-001"
    self_id = "self-reviewer-001"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.post(
            "/api/v1/reviews/decisions",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "decision_id": decision_id,
                "idempotency_key": idempotency_key,
                "case_id": case_id,
                "reviewer_id": self_id,
                "subject_author_id": self_id,  # same ID → independence violation
                "outcome": "ACCEPT",
            },
        )

    assert response.status_code == 403, (
        f"Expected 403 REVIEW_INDEPENDENCE_DENIED, got {response.status_code}: {response.text}"
    )

    body = response.json()
    # FastAPI wraps HTTPException detail in {"detail": ...}
    detail = body.get("detail", body)

    assert detail.get("error") == "REVIEW_INDEPENDENCE_DENIED", (
        f"Expected error=REVIEW_INDEPENDENCE_DENIED, got: {detail}"
    )
    assert detail.get("guard_assertion_id") == "INV-SPS-REV-001", (
        f"Expected guard_assertion_id=INV-SPS-REV-001, got: {detail}"
    )
    assert detail.get("normalized_business_invariants") == ["INV-008"], (
        f"Expected normalized_business_invariants=['INV-008'], got: {detail}"
    )

    # No DB row must have been written — guard fires before INSERT
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(ReviewDecision, decision_id)
        assert row is None, (
            f"Expected no review_decisions row for decision_id={decision_id}, "
            f"but a row was found: {row}"
        )


async def _run_distinct_reviewer_test() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-DISTINCT-REVIEWER-001"
    decision_id = "DEC-DISTINCT-REVIEWER-001"
    idempotency_key = "idem/distinct-reviewer-001"

    # Seed the parent permit_case row — review_decisions has a FK constraint to permit_cases.
    # The independence guard passes (distinct IDs) so the endpoint will reach the INSERT.
    _seed_permit_case(case_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.post(
            "/api/v1/reviews/decisions",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "decision_id": decision_id,
                "idempotency_key": idempotency_key,
                "case_id": case_id,
                "reviewer_id": "reviewer-001",
                "subject_author_id": "author-001",  # distinct → guard passes
                "outcome": "ACCEPT",
            },
        )

    # Signal delivery failure is expected (no Temporal worker running).
    # The Postgres write is authoritative; response must still be 201.
    assert response.status_code == 201, (
        f"Expected 201 (signal failure is swallowed), got {response.status_code}: {response.text}"
    )

    # Assert DB row was written with reviewer_independence_status=PASS
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(ReviewDecision, decision_id)
        assert row is not None, (
            f"Expected review_decisions row for decision_id={decision_id}, but none found"
        )
        assert row.reviewer_independence_status == "PASS", (
            f"Expected reviewer_independence_status=PASS, got: {row.reviewer_independence_status}"
        )
