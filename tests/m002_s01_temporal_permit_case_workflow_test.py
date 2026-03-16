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
from sps.db.models import PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_review_decision,
)
from sps.workflows.permit_case.contracts import (
    PermitCaseWorkflowInput,
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
    """Wait until Postgres accepts connections (docker-compose can take a few seconds)."""

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


def _clear_case_row(case_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.execute(sa.delete(PermitCase).where(PermitCase.case_id == case_id))
        session.commit()


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


async def _wait_for_permit_case_exists(case_id: str, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            if session.get(PermitCase, case_id) is not None:
                return
        await asyncio.sleep(0.25)

    raise AssertionError(f"permit_cases row not found for case_id={case_id} within {timeout_s}s")


def test_temporal_permit_case_workflow_signal_wait_integration() -> None:
    """Slice-level integration proof.

    Proves:
    - workflow starts and executes the DB bootstrap activity
    - workflow blocks waiting for ReviewDecision signal
    - sending signal resumes workflow and completes with an acknowledgment payload
    """

    asyncio.run(_run_integration())


async def _run_integration() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()

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

        _clear_case_row(case_id)

        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        # Assert side effect from bootstrap activity.
        await _wait_for_permit_case_exists(case_id)

        # Assert workflow is still running (waiting on signal).
        desc = await handle.describe()
        assert (
            desc.status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_RUNNING
        ), f"unexpected status: {desc.status}"

        # Stronger: the workflow should not complete before we send the signal.
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

        raw_result = await asyncio.wait_for(handle.result(), timeout=20.0)
        result = (
            raw_result
            if isinstance(raw_result, PermitCaseWorkflowResult)
            else PermitCaseWorkflowResult.model_validate(raw_result)
        )

        assert result.review_signal is not None
        assert result.review_signal.decision_outcome == ReviewDecisionOutcome.ACCEPT
        assert result.review_signal.reviewer_id == "reviewer-1"
        assert result.final_result.result == "applied"

        # Stronger: confirm the guarded transition applied in Postgres.
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            reloaded = session.get(PermitCase, case_id)
            assert reloaded is not None
            assert reloaded.case_state == "APPROVED_FOR_SUBMISSION"

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
