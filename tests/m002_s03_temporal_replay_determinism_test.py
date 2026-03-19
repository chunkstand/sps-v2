from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from temporalio.api.enums.v1.workflow_pb2 import WorkflowExecutionStatus
from temporalio.worker import Worker

import ulid

from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
)
from sps.workflows.permit_case.contracts import (
    PermitCaseWorkflowResult,
    ReviewDecisionOutcome,
    ReviewDecisionSignal,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client

from tests.helpers.temporal_replay import replay_permit_case_workflow_history


pytestmark = pytest.mark.integration

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    engine = get_engine()

    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover - only hits when infra is slow
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError(f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})")


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    # We keep this narrowly-scoped to the PermitCase workflow tables we touch.
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

    raise RuntimeError(f"Temporal not ready after {timeout_s}s (last_exc={type(last_exc).__name__})")


def _transition_request_id(*, workflow_id: str, run_id: str, transition: str, attempt: int) -> str:
    return f"{workflow_id}/{run_id}/{transition}/attempt-{attempt}"


async def _wait_for_permit_case_exists(case_id: str, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            if session.get(PermitCase, case_id) is not None:
                return
        await asyncio.sleep(0.25)

    raise AssertionError(f"permit_cases row not found for case_id={case_id} within {timeout_s}s")


def _seed_review_decision(case_id: str, decision_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            ReviewDecision(
                decision_id=decision_id,
                schema_version="1.0",
                case_id=case_id,
                object_type="permit_case",
                object_id=case_id,
                decision_outcome="ACCEPT",
                reviewer_id="reviewer-1",
                subject_author_id="author-1",
                reviewer_independence_status="PASS",
                evidence_ids=[],
                contradiction_resolution=None,
                dissent_flag=False,
                notes="integration test",
                decision_at=sa.func.now(),
                idempotency_key=f"idem/{decision_id}",
            )
        )
        session.commit()


def test_temporal_permit_case_offline_replay_determinism_integration() -> None:
    """Determinism closure proof.

    Run PermitCaseWorkflow to completion on real Temporal+Postgres, then replay the
    captured history offline with temporalio.worker.Replayer.

    If workflow code becomes non-deterministic, the replay step fails with a
    divergence error pointing at the first incompatible history event.
    """

    asyncio.run(_run_integration())


async def _run_integration() -> None:
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

        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            {"case_id": case_id},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        run_id = handle.first_execution_run_id or handle.run_id
        assert run_id is not None

        correlation_id = f"{workflow_id}:{run_id}"
        transition_name = "review_pending_to_approved_for_submission"
        req1 = _transition_request_id(
            workflow_id=workflow_id, run_id=run_id, transition=transition_name, attempt=1
        )
        req2 = _transition_request_id(
            workflow_id=workflow_id, run_id=run_id, transition=transition_name, attempt=2
        )
        decision_id = f"DEC-{ulid.new()}"

        # Sanity: we expect the workflow to be running (waiting on the signal).
        await _wait_for_permit_case_exists(case_id)
        desc = await handle.describe()
        assert (
            desc.status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_RUNNING
        ), f"unexpected status before signal: {desc.status}"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(handle.result(), timeout=1.0)

        _seed_review_decision(case_id, decision_id)

        await handle.signal(
            PermitCaseWorkflow.review_decision,
            ReviewDecisionSignal(
                decision_id=decision_id,
                decision_outcome=ReviewDecisionOutcome.ACCEPT,
                reviewer_id="reviewer-1",
                notes="integration test",
            ),
        )

        raw_result = await asyncio.wait_for(handle.result(), timeout=30.0)
        result = (
            raw_result
            if isinstance(raw_result, PermitCaseWorkflowResult)
            else PermitCaseWorkflowResult.model_validate(raw_result)
        )

        assert result.case_id == case_id
        assert result.correlation_id == correlation_id
        assert result.initial_request_id == req1
        assert result.final_request_id == req2
        assert result.review_decision_id == decision_id
        assert result.final_result.result == "applied"

        # Must-have: fetch history from a real workflow run.
        history = await handle.fetch_history()

        # Must-have: offline replay determinism proof.
        try:
            await replay_permit_case_workflow_history(history)
        except Exception as exc:
            raise AssertionError(
                "offline replay failed (non-deterministic workflow code?) "
                f"workflow_id={workflow_id} run_id={run_id}"
            ) from exc

        # Must-have: assert at least one durable Postgres signal for this correlation_id.
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            reloaded = session.get(PermitCase, case_id)
            assert reloaded is not None
            assert reloaded.case_state == "APPROVED_FOR_SUBMISSION"

            ledgers = (
                session.query(CaseTransitionLedger)
                .filter(CaseTransitionLedger.correlation_id == correlation_id)
                .order_by(CaseTransitionLedger.occurred_at.asc())
                .all()
            )
            assert len(ledgers) == 2
            assert {row.transition_id for row in ledgers} == {req1, req2}

            review = session.get(ReviewDecision, decision_id)
            assert review is not None
            assert review.case_id == case_id

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
