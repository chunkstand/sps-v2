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
from sps.db.models import CaseTransitionLedger, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_review_decision,
)
from sps.workflows.permit_case.contracts import (
    PermitCaseWorkflowResult,
    ReviewDecisionOutcome,
    ReviewDecisionSignal,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client


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
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError(f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})")


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


def _transition_request_id(*, workflow_id: str, run_id: str, transition: str, attempt: int) -> str:
    return f"{workflow_id}/{run_id}/{transition}/attempt-{attempt}"


async def _wait_for_ledger_row(transition_id: str, timeout_s: float = 10.0) -> CaseTransitionLedger:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            row = session.get(CaseTransitionLedger, transition_id)
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise AssertionError(
        f"case_transition_ledger row not found for transition_id={transition_id} within {timeout_s}s"
    )


def test_temporal_guarded_transition_workflow_denial_signal_unblock_integration() -> None:
    """End-to-end proof: denial → wait → signal → persist → apply.

    Proves:
      - guarded transition denial is durable (ledger row exists while workflow is waiting)
      - ReviewDecision signal causes durable review persistence and unblocks the guarded transition
      - Postgres state and ledger reflect one denied + one applied attempt for the workflow run
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
            persist_review_decision,
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
            workflow_id=workflow_id,
            run_id=run_id,
            transition=transition_name,
            attempt=1,
        )
        req2 = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition=transition_name,
            attempt=2,
        )

        # Wait for the denial ledger row (proves durable denial while workflow is still running).
        denied_row = await _wait_for_ledger_row(req1)
        assert denied_row.event_type == "APPROVAL_GATE_DENIED"
        assert denied_row.correlation_id == correlation_id

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            seeded = session.get(PermitCase, case_id)
            assert seeded is not None
            assert seeded.case_state == "REVIEW_PENDING"

        desc = await handle.describe()
        assert (
            desc.status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_RUNNING
        ), f"unexpected status: {desc.status}"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(handle.result(), timeout=1.0)

        await handle.signal(
            PermitCaseWorkflow.review_decision,
            ReviewDecisionSignal(
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
        assert result.final_result.result == "applied"

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

            by_id = {row.transition_id: row for row in ledgers}
            assert set(by_id.keys()) == {req1, req2}
            assert by_id[req1].event_type == "APPROVAL_GATE_DENIED"
            assert by_id[req2].event_type == "CASE_STATE_CHANGED"

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
