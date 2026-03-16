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

from sps import failpoints
from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
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
        except Exception as exc:  # pragma: no cover - only hits when infra is slow
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
            sa.text("TRUNCATE TABLE case_transition_ledger, review_decisions, permit_cases CASCADE")
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


async def _wait_for_failpoint_fired(key: str, timeout_s: float = 15.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if failpoints.was_fired(key):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"failpoint did not fire within {timeout_s}s (key={key})")


def test_temporal_activity_retry_idempotency_post_commit_failpoint_integration() -> None:
    """Prove DB idempotency under real Temporal activity retry.

    We deliberately raise *after commit* inside targeted activities so Temporal retries
    them. The assertions then prove the authoritative Postgres side effects are still
    exactly-once.
    """

    asyncio.run(_run_integration())


async def _run_integration() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    client = await _connect_temporal_with_retry()

    # Start the workflow first so we can compute deterministic keys (they include run_id),
    # then configure failpoints before the in-process worker starts executing tasks.
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
    req1 = _transition_request_id(workflow_id=workflow_id, run_id=run_id, transition=transition_name, attempt=1)
    req2 = _transition_request_id(workflow_id=workflow_id, run_id=run_id, transition=transition_name, attempt=2)

    review_idempotency_key = f"review/{workflow_id}/{run_id}"

    apply_failpoint_key = f"apply_state_transition.after_commit/{req2}"
    review_failpoint_key = f"persist_review_decision.after_commit/{review_idempotency_key}"

    prior_enable = os.environ.get("SPS_ENABLE_TEST_FAILPOINTS")
    prior_keys = os.environ.get("SPS_TEST_FAILPOINT_KEYS")

    os.environ["SPS_ENABLE_TEST_FAILPOINTS"] = "1"
    os.environ["SPS_TEST_FAILPOINT_KEYS"] = f"{review_failpoint_key},{apply_failpoint_key}"
    failpoints.reset_for_tests()

    executor = ThreadPoolExecutor(max_workers=10)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[ensure_permit_case_exists, apply_state_transition, persist_review_decision],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    try:
        # Sanity: we expect the workflow to be running (it should reach the signal wait).
        deadline = time.time() + 30.0
        while time.time() < deadline:
            desc = await handle.describe()
            if desc.status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_RUNNING:
                break
            await asyncio.sleep(0.2)
        else:
            raise AssertionError("workflow did not enter RUNNING state in time")

        # Ensure the denial ledger row exists before sending the review decision.
        SessionLocal = get_sessionmaker()
        denial_deadline = time.time() + 20.0
        while time.time() < denial_deadline:
            with SessionLocal() as session:
                if session.get(CaseTransitionLedger, req1) is not None:
                    break
            await asyncio.sleep(0.25)
        else:
            raise AssertionError(f"expected denial ledger row not found for transition_id={req1}")

        await handle.signal(
            PermitCaseWorkflow.review_decision,
            ReviewDecisionSignal(
                decision_outcome=ReviewDecisionOutcome.ACCEPT,
                reviewer_id="reviewer-1",
                notes="activity retry idempotency integration test",
            ),
        )

        # Must-have: failpoints fire after commit. Once the failpoint has fired we should
        # be able to observe the committed DB row immediately.
        await _wait_for_failpoint_fired(review_failpoint_key)
        with SessionLocal() as session:
            review_rows = (
                session.query(ReviewDecision)
                .filter(ReviewDecision.idempotency_key == review_idempotency_key)
                .all()
            )
            assert len(review_rows) == 1

        await _wait_for_failpoint_fired(apply_failpoint_key)
        with SessionLocal() as session:
            ledger = session.get(CaseTransitionLedger, req2)
            assert ledger is not None
            # The case state mutation happens in the same committed transaction.
            case = session.get(PermitCase, case_id)
            assert case is not None
            assert case.case_state == "APPROVED_FOR_SUBMISSION"

        raw_result = await asyncio.wait_for(handle.result(), timeout=45.0)
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

        # Observability + proof: Temporal history should include the failpoint exception message
        # for the first attempt of each targeted activity.
        history = await handle.fetch_history()
        history_dict = history.to_json_dict()

        def _collect_strings(value, out: list[str]) -> None:  # type: ignore[no-untyped-def]
            if value is None:
                return
            if isinstance(value, str):
                out.append(value)
                return
            if isinstance(value, dict):
                for v in value.values():
                    _collect_strings(v, out)
                return
            if isinstance(value, list):
                for v in value:
                    _collect_strings(v, out)
                return

        strings: list[str] = []
        _collect_strings(history_dict, strings)
        history_text = "\n".join(strings)

        assert f"FAILPOINT_FIRED key={review_failpoint_key}" in history_text
        assert f"FAILPOINT_FIRED key={apply_failpoint_key}" in history_text

        # Must-have: prove the activities were retried (post-commit crash then retry).
        assert failpoints.get_seen_count(review_failpoint_key) >= 2
        assert failpoints.get_seen_count(apply_failpoint_key) >= 2

        # Must-have: prove exactly-once Postgres effects.
        with SessionLocal() as session:
            ledgers = (
                session.query(CaseTransitionLedger)
                .filter(CaseTransitionLedger.correlation_id == correlation_id)
                .order_by(CaseTransitionLedger.occurred_at.asc())
                .all()
            )
            assert len(ledgers) == 2
            assert {row.transition_id for row in ledgers} == {req1, req2}

            review_rows = (
                session.query(ReviewDecision)
                .filter(ReviewDecision.idempotency_key == review_idempotency_key)
                .all()
            )
            assert len(review_rows) == 1

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)

        # Clean up env so other integration tests are not impacted.
        if prior_enable is None:
            os.environ.pop("SPS_ENABLE_TEST_FAILPOINTS", None)
        else:
            os.environ["SPS_ENABLE_TEST_FAILPOINTS"] = prior_enable

        if prior_keys is None:
            os.environ.pop("SPS_TEST_FAILPOINT_KEYS", None)
        else:
            os.environ["SPS_TEST_FAILPOINT_KEYS"] = prior_keys
