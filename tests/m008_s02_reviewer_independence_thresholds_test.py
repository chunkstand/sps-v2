"""M008 / S02 integration tests: Rolling-quarter reviewer independence thresholds.

Proves 90-day rolling-window enforcement on POST /api/v1/reviews/decisions:

  1. PASS: no repeated author-reviewer pairs -> reviewer_independence_status=PASS
  2. WARNING: repeated pair rate > 25% -> reviewer_independence_status=WARNING
  3. ESCALATION_REQUIRED: repeated pair rate > 35% -> reviewer_independence_status=ESCALATION_REQUIRED
  4. BLOCKED: repeated pair rate > 50% -> 403 + guard_assertion_id=INV-SPS-REV-001

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: mirrors m003_s02_reviewer_independence_test.py (real Postgres, no Temporal worker needed).

## Observability Impact
Signals added/changed by this task:
  - WARNING log line: reviewer_api.independence_warning (threshold warning)
  - WARNING log line: reviewer_api.independence_escalation (threshold escalation)
  - WARNING log line: reviewer_api.independence_blocked (threshold block)

Failure state visibility:
  - 403 response body contains guard_assertion_id=INV-SPS-REV-001 + blocked_reason
"""
from __future__ import annotations

import asyncio
import os
import time
import datetime as dt

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.api.routes import reviews as reviews_module
from sps.config import get_settings
from sps.db.models import PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

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
    """Insert a minimal PermitCase row so review_decisions FK constraint is satisfied."""
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


def _seed_review_decision(
    *,
    case_id: str,
    decision_id: str,
    reviewer_id: str,
    subject_author_id: str,
    decision_at: dt.datetime,
) -> None:
    _seed_permit_case(case_id)
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = ReviewDecision(
            decision_id=decision_id,
            schema_version="1.0",
            case_id=case_id,
            object_type="permit_case",
            object_id=case_id,
            decision_outcome="ACCEPT",
            reviewer_id=reviewer_id,
            subject_author_id=subject_author_id,
            reviewer_independence_status="PASS",
            evidence_ids=[],
            contradiction_resolution=None,
            dissent_flag=False,
            notes=None,
            decision_at=decision_at,
            idempotency_key=f"seed/{decision_id}",
        )
        session.add(row)
        session.commit()


def _seed_history(
    *,
    reviewer_id: str,
    subject_author_id: str,
    pair_count: int,
    other_count: int,
    decision_at: dt.datetime,
) -> None:
    for idx in range(pair_count):
        _seed_review_decision(
            case_id=f"CASE-PAIR-{idx}",
            decision_id=f"DEC-PAIR-{idx}",
            reviewer_id=reviewer_id,
            subject_author_id=subject_author_id,
            decision_at=decision_at,
        )
    for idx in range(other_count):
        _seed_review_decision(
            case_id=f"CASE-OTHER-{idx}",
            decision_id=f"DEC-OTHER-{idx}",
            reviewer_id=f"reviewer-other-{idx}",
            subject_author_id=f"author-other-{idx}",
            decision_at=decision_at,
        )


def _capture_warning_messages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    messages: list[str] = []

    def _capture(message: str, *args: object, **kwargs: object) -> None:
        if args:
            message = message % args
        messages.append(message)

    monkeypatch.setattr(reviews_module.logger, "warning", _capture)
    return messages


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_independence_pass_status_persisted() -> None:
    asyncio.run(_run_pass_test())


def test_independence_warning_status_persisted(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_run_warning_test(monkeypatch))


def test_independence_escalation_status_persisted(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_run_escalation_test(monkeypatch))


def test_independence_blocked_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_run_blocked_test(monkeypatch))


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _post_decision(
    *,
    decision_id: str,
    case_id: str,
    reviewer_id: str,
    subject_author_id: str,
) -> httpx.Response:
    settings = get_settings()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        return await api_client.post(
            "/api/v1/reviews/decisions",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "decision_id": decision_id,
                "idempotency_key": f"idem/{decision_id}",
                "case_id": case_id,
                "reviewer_id": reviewer_id,
                "subject_author_id": subject_author_id,
                "outcome": "ACCEPT",
            },
        )


async def _run_pass_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-PASS-001"
    decision_id = "DEC-PASS-001"

    _seed_permit_case(case_id)

    response = await _post_decision(
        decision_id=decision_id,
        case_id=case_id,
        reviewer_id="reviewer-pass",
        subject_author_id="author-pass",
    )

    assert response.status_code == 201, (
        f"Expected 201 for PASS, got {response.status_code}: {response.text}"
    )

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(ReviewDecision, decision_id)
        assert row is not None, "Expected review_decisions row for PASS decision"
        assert row.reviewer_independence_status == "PASS"
        assert row.subject_author_id == "author-pass"


async def _run_warning_test(monkeypatch: pytest.MonkeyPatch) -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    now = dt.datetime.now(tz=dt.UTC)
    reviewer_id = "reviewer-warning"
    subject_author_id = "author-warning"

    _seed_history(
        reviewer_id=reviewer_id,
        subject_author_id=subject_author_id,
        pair_count=2,
        other_count=3,
        decision_at=now - dt.timedelta(days=1),
    )

    case_id = "CASE-WARN-001"
    decision_id = "DEC-WARN-001"
    _seed_permit_case(case_id)

    warning_messages = _capture_warning_messages(monkeypatch)
    response = await _post_decision(
        decision_id=decision_id,
        case_id=case_id,
        reviewer_id=reviewer_id,
        subject_author_id=subject_author_id,
    )

    assert response.status_code == 201, (
        f"Expected 201 for WARNING, got {response.status_code}: {response.text}"
    )
    assert any(
        "reviewer_api.independence_warning" in message for message in warning_messages
    ), f"Expected independence warning log, got: {warning_messages}"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(ReviewDecision, decision_id)
        assert row is not None, "Expected review_decisions row for WARNING decision"
        assert row.reviewer_independence_status == "WARNING"
        assert row.subject_author_id == subject_author_id


async def _run_escalation_test(monkeypatch: pytest.MonkeyPatch) -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    now = dt.datetime.now(tz=dt.UTC)
    reviewer_id = "reviewer-escalation"
    subject_author_id = "author-escalation"

    _seed_history(
        reviewer_id=reviewer_id,
        subject_author_id=subject_author_id,
        pair_count=3,
        other_count=2,
        decision_at=now - dt.timedelta(days=1),
    )

    case_id = "CASE-ESC-001"
    decision_id = "DEC-ESC-001"
    _seed_permit_case(case_id)

    warning_messages = _capture_warning_messages(monkeypatch)
    response = await _post_decision(
        decision_id=decision_id,
        case_id=case_id,
        reviewer_id=reviewer_id,
        subject_author_id=subject_author_id,
    )

    assert response.status_code == 201, (
        f"Expected 201 for ESCALATION_REQUIRED, got {response.status_code}: {response.text}"
    )
    assert any(
        "reviewer_api.independence_escalation" in message for message in warning_messages
    ), f"Expected independence escalation log, got: {warning_messages}"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(ReviewDecision, decision_id)
        assert row is not None, "Expected review_decisions row for escalation decision"
        assert row.reviewer_independence_status == "ESCALATION_REQUIRED"
        assert row.subject_author_id == subject_author_id


async def _run_blocked_test(monkeypatch: pytest.MonkeyPatch) -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    now = dt.datetime.now(tz=dt.UTC)
    reviewer_id = "reviewer-blocked"
    subject_author_id = "author-blocked"

    _seed_history(
        reviewer_id=reviewer_id,
        subject_author_id=subject_author_id,
        pair_count=4,
        other_count=1,
        decision_at=now - dt.timedelta(days=1),
    )

    case_id = "CASE-BLOCK-001"
    decision_id = "DEC-BLOCK-001"
    _seed_permit_case(case_id)

    warning_messages = _capture_warning_messages(monkeypatch)
    response = await _post_decision(
        decision_id=decision_id,
        case_id=case_id,
        reviewer_id=reviewer_id,
        subject_author_id=subject_author_id,
    )

    assert response.status_code == 403, (
        f"Expected 403 for BLOCKED, got {response.status_code}: {response.text}"
    )
    assert any(
        "reviewer_api.independence_blocked" in message for message in warning_messages
    ), f"Expected independence blocked log, got: {warning_messages}"

    body = response.json()
    detail = body.get("detail", body)
    assert detail.get("guard_assertion_id") == "INV-SPS-REV-001"
    assert detail.get("blocked_reason") == "INDEPENDENCE_THRESHOLD_BLOCKED"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = session.get(ReviewDecision, decision_id)
        assert row is None, "Expected no review_decisions row for blocked decision"
