"""M003 / S01 integration test: Reviewer API authority boundary.

Proves R006 against a real docker-compose stack:

  HTTP POST /api/v1/reviews/decisions
    → Postgres review_decisions row
    → Temporal ReviewDecision signal
    → workflow resumes
    → APPROVED_FOR_SUBMISSION in case_transition_ledger

Also proves the 409 idempotency-conflict path.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: follows m002_s02 (real Temporal worker + real Postgres).
"""

from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from temporalio.worker import Worker

import ulid

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
)
from sps.workflows.permit_case.contracts import (
    PermitCaseWorkflowResult,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client


pytestmark = pytest.mark.integration

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers (mirrors m002_s02 pattern)
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


async def _connect_temporal_with_retry(timeout_s: float = 30.0):
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            return await connect_client()
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            await asyncio.sleep(0.5)

    raise RuntimeError(
        f"Temporal not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


async def _wait_for_ledger_row_by_event(
    *,
    case_id: str,
    event_type: str,
    to_state: str | None = None,
    timeout_s: float = 30.0,
) -> CaseTransitionLedger:
    """Poll for a ledger row matching event_type (and optionally to_state) for the given case."""
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            q = session.query(CaseTransitionLedger).filter(
                CaseTransitionLedger.case_id == case_id,
                CaseTransitionLedger.event_type == event_type,
            )
            if to_state is not None:
                q = q.filter(CaseTransitionLedger.to_state == to_state)
            row = q.first()
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise AssertionError(
        f"case_transition_ledger row not found: case_id={case_id} "
        f"event_type={event_type} to_state={to_state} within {timeout_s}s"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_reviewer_api_unblocks_workflow() -> None:
    """Happy path: POST /api/v1/reviews/decisions → workflow reaches APPROVED_FOR_SUBMISSION.

    Checks:
    - HTTP 201 from the reviewer API endpoint
    - review_decisions row persisted in Postgres
    - workflow result is 'applied'
    - case_transition_ledger has CASE_STATE_CHANGED with to_state=APPROVED_FOR_SUBMISSION
    """
    asyncio.run(_run_unblock_test())


def test_reviewer_api_idempotency_conflict_409() -> None:
    """Conflict path: second POST with same idempotency_key but different decision_id → 409."""
    asyncio.run(_run_conflict_test())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_unblock_test() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    client = await _connect_temporal_with_retry()

    executor = ThreadPoolExecutor(max_workers=10)
    # Note: activities list excludes persist_review_decision — the API is the sole writer now.
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            apply_state_transition,
        ],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    try:
        case_id = f"CASE-{ulid.new()}"
        workflow_id = permit_case_workflow_id(case_id)

        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            {"case_id": case_id},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        # Wait for the APPROVAL_GATE_DENIED ledger row — proves the workflow is paused
        # waiting for the review signal.
        await _wait_for_ledger_row_by_event(
            case_id=case_id,
            event_type="APPROVAL_GATE_DENIED",
            timeout_s=30.0,
        )

        # Verify workflow is running (not yet resolved).
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(handle.result(), timeout=1.0)

        # --- Call the HTTP authority boundary ---
        decision_id = f"DEC-{ulid.new()}"
        idempotency_key = f"idem/{workflow_id}"

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
            response = await api_client.post(
                "/api/v1/reviews/decisions",
                headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
                json={
                    "decision_id": decision_id,
                    "idempotency_key": idempotency_key,
                    "case_id": case_id,
                    "reviewer_id": "reviewer-integration-test",
                    "subject_author_id": "author-of-the-case",
                    "outcome": "ACCEPT",
                },
            )

        assert response.status_code == 201, (
            f"Expected 201 from reviewer API, got {response.status_code}: {response.text}"
        )

        resp_body = response.json()
        assert resp_body["decision_id"] == decision_id
        assert resp_body["case_id"] == case_id
        assert resp_body["outcome"] == "ACCEPT"
        assert resp_body["idempotency_key"] == idempotency_key

        # Assert Postgres review_decisions row
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            row = session.get(ReviewDecision, decision_id)
            assert row is not None, f"review_decisions row not found for decision_id={decision_id}"
            assert row.case_id == case_id
            assert row.decision_outcome == "ACCEPT"
            assert row.idempotency_key == idempotency_key

        # Wait for workflow to complete (the signal should have been delivered above)
        raw_result = await asyncio.wait_for(handle.result(), timeout=30.0)
        result = (
            raw_result
            if isinstance(raw_result, PermitCaseWorkflowResult)
            else PermitCaseWorkflowResult.model_validate(raw_result)
        )

        assert result.case_id == case_id
        assert result.final_result.result == "applied", (
            f"Expected final_result.result='applied', got: {result.final_result}"
        )

        # Assert case_transition_ledger has CASE_STATE_CHANGED → APPROVED_FOR_SUBMISSION
        with SessionLocal() as session:
            approved_row = (
                session.query(CaseTransitionLedger)
                .filter(
                    CaseTransitionLedger.case_id == case_id,
                    CaseTransitionLedger.event_type == "CASE_STATE_CHANGED",
                    CaseTransitionLedger.to_state == "APPROVED_FOR_SUBMISSION",
                )
                .first()
            )
            assert approved_row is not None, (
                "Expected CASE_STATE_CHANGED/APPROVED_FOR_SUBMISSION row in case_transition_ledger"
            )

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)


async def _run_conflict_test() -> None:
    """Proves 409 IDEMPOTENCY_CONFLICT when same idempotency_key used with a different decision_id."""
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    client = await _connect_temporal_with_retry()

    executor = ThreadPoolExecutor(max_workers=10)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            apply_state_transition,
        ],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    try:
        case_id = f"CASE-{ulid.new()}"
        workflow_id = permit_case_workflow_id(case_id)

        await client.start_workflow(
            PermitCaseWorkflow.run,
            {"case_id": case_id},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        # Wait for workflow to be in REVIEW_PENDING (paused waiting for signal).
        await _wait_for_ledger_row_by_event(
            case_id=case_id,
            event_type="APPROVAL_GATE_DENIED",
            timeout_s=30.0,
        )

        decision_id_first = f"DEC-FIRST-{ulid.new()}"
        decision_id_second = f"DEC-SECOND-{ulid.new()}"
        idempotency_key = f"idem/{workflow_id}"

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
            # First POST — should create successfully.
            r1 = await api_client.post(
                "/api/v1/reviews/decisions",
                headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
                json={
                    "decision_id": decision_id_first,
                    "idempotency_key": idempotency_key,
                    "case_id": case_id,
                    "reviewer_id": "reviewer-conflict-test",
                    "subject_author_id": "author-of-the-case",
                    "outcome": "ACCEPT",
                },
            )
            assert r1.status_code == 201, f"First POST should be 201, got {r1.status_code}: {r1.text}"

            # Second POST — same idempotency_key, different decision_id → 409.
            r2 = await api_client.post(
                "/api/v1/reviews/decisions",
                headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
                json={
                    "decision_id": decision_id_second,
                    "idempotency_key": idempotency_key,
                    "case_id": case_id,
                    "reviewer_id": "reviewer-conflict-test",
                    "subject_author_id": "author-of-the-case",
                    "outcome": "ACCEPT",
                },
            )

        assert r2.status_code == 409, (
            f"Expected 409 IDEMPOTENCY_CONFLICT, got {r2.status_code}: {r2.text}"
        )
        conflict_body = r2.json()
        # FastAPI wraps HTTPException detail in {"detail": ...}
        detail = conflict_body.get("detail", conflict_body)
        assert detail.get("error") == "IDEMPOTENCY_CONFLICT", (
            f"Expected error=IDEMPOTENCY_CONFLICT in response body, got: {conflict_body}"
        )
        assert detail.get("existing_decision_id") == decision_id_first, (
            f"Expected existing_decision_id={decision_id_first}, got: {detail}"
        )
        assert detail.get("idempotency_key") == idempotency_key, (
            f"Expected idempotency_key={idempotency_key}, got: {detail}"
        )

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
