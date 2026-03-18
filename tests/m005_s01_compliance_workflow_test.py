"""M005 / S01 compliance fixture + workflow tests.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run Temporal-backed tests.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timezone

import httpx
import pytest
import sqlalchemy as sa
import ulid
from alembic import command
from alembic.config import Config
from temporalio.worker import Worker

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, ComplianceEvaluation, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.fixtures.phase4 import (
    PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV,
    select_jurisdiction_fixtures,
    select_requirement_fixtures,
)
from sps.fixtures.phase5 import (
    PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV,
    load_compliance_fixtures,
    select_compliance_fixtures,
)
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_compliance_evaluation,
    persist_jurisdiction_resolutions,
    persist_requirement_sets,
)
from sps.workflows.permit_case.contracts import (
    ActorType,
    CaseState,
    StateTransitionRequest,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client
from tests.helpers.auth_tokens import build_jwt


# ---------------------------------------------------------------------------
# Fixtures schema validation
# ---------------------------------------------------------------------------


def test_phase5_fixture_schema_loads() -> None:
    dataset = load_compliance_fixtures()

    assert dataset.evaluations, "compliance fixtures should not be empty"

    evaluation = dataset.evaluations[0]
    assert evaluation.schema_version
    assert isinstance(evaluation.evaluated_at, datetime)
    assert evaluation.rule_results
    assert evaluation.blockers is not None
    assert evaluation.warnings is not None
    assert evaluation.provenance is not None

    rule_result = evaluation.rule_results[0]
    assert rule_result.rule_id
    assert rule_result.outcome is not None
    assert rule_result.provenance is not None
    assert rule_result.evidence_payload is not None

    blocker = evaluation.blockers[0]
    assert blocker.issue_id
    assert blocker.rule_id
    assert blocker.provenance is not None

    warning = evaluation.warnings[0]
    assert warning.issue_id
    assert warning.rule_id
    assert warning.provenance is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _ListHandler(logging.Handler):
    def __init__(self, messages: list[str]) -> None:
        super().__init__(level=logging.INFO)
        self._messages = messages

    def emit(self, record: logging.LogRecord) -> None:
        self._messages.append(record.getMessage())


def _capture_logger(
    logger_name: str,
) -> tuple[list[str], logging.Logger, logging.Handler, int, bool, bool]:
    logger = logging.getLogger(logger_name)
    messages: list[str] = []
    handler = _ListHandler(messages)
    old_level = logger.level
    old_disabled = logger.disabled
    old_propagate = logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.disabled = False
    logger.propagate = True
    return messages, logger, handler, old_level, old_disabled, old_propagate


def _require_temporal_integration() -> None:
    if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
        pytest.skip(
            "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
            allow_module_level=False,
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
                "TRUNCATE TABLE compliance_evaluations, case_transition_ledger, "
                "jurisdiction_resolutions, requirement_sets, projects, permit_cases CASCADE"
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


async def _wait_for_ledger_row_by_state(
    *, case_id: str, to_state: str, timeout_s: float = 30.0
) -> CaseTransitionLedger:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            row = (
                session.query(CaseTransitionLedger)
                .filter(
                    CaseTransitionLedger.case_id == case_id,
                    CaseTransitionLedger.event_type == "CASE_STATE_CHANGED",
                    CaseTransitionLedger.to_state == to_state,
                )
                .first()
            )
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise RuntimeError(f"ledger row not found for case_id={case_id} to_state={to_state}")


def _auth_headers() -> dict[str, str]:
    token = build_jwt(subject="intake-user", roles=["intake"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _configure_fixture_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV, "CASE-EXAMPLE-001")
    monkeypatch.setenv(PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV, "CASE-EXAMPLE-001")


# ---------------------------------------------------------------------------
# Integration: workflow progression + API
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_workflow_progression(caplog: pytest.LogCaptureFixture) -> None:
    _require_temporal_integration()

    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, logger="sps.workflows.permit_case.activities_impl")
    caplog.set_level(logging.INFO, logger="sps.api.routes.cases_impl")
    asyncio.run(_run_workflow_progression(caplog))


async def _run_workflow_progression(caplog: pytest.LogCaptureFixture) -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    (
        activity_messages,
        activity_logger,
        activity_handler,
        activity_level,
        activity_disabled,
        activity_propagate,
    ) = _capture_logger("sps.workflows.permit_case.activities_impl")
    (
        api_messages,
        api_logger,
        api_handler,
        api_level,
        api_disabled,
        api_propagate,
    ) = _capture_logger("sps.api.routes.cases_impl")

    client = await _connect_temporal_with_retry()
    handle = None

    executor = ThreadPoolExecutor(max_workers=10)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            persist_jurisdiction_resolutions,
            persist_requirement_sets,
            persist_compliance_evaluation,
            apply_state_transition,
        ],
        activity_executor=executor,
    )
    worker_task = asyncio.create_task(worker.run())

    try:
        case_id = f"CASE-COMP-{ulid.new()}"
        jurisdiction_fixtures, jurisdiction_fixture_case_id = select_jurisdiction_fixtures(case_id)
        requirement_fixtures, requirement_fixture_case_id = select_requirement_fixtures(case_id)
        compliance_fixtures, compliance_fixture_case_id = select_compliance_fixtures(case_id)
        assert jurisdiction_fixture_case_id == "CASE-EXAMPLE-001"
        assert requirement_fixture_case_id == "CASE-EXAMPLE-001"
        assert compliance_fixture_case_id == "CASE-EXAMPLE-001"

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            session.add(
                PermitCase(
                    case_id=case_id,
                    tenant_id="tenant-local",
                    project_id=f"project-{case_id}",
                    case_state=CaseState.INTAKE_COMPLETE.value,
                    review_state="PENDING",
                    submission_mode="AUTOMATED",
                    portal_support_level="FULLY_SUPPORTED",
                    current_package_id=None,
                    current_release_profile="default",
                    legal_hold=False,
                    closure_reason=None,
                )
            )
            session.commit()

        workflow_id = f"{permit_case_workflow_id(case_id)}-{ulid.new()}"
        headers = _auth_headers()
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            {"case_id": case_id},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        await _wait_for_ledger_row_by_state(case_id=case_id, to_state="RESEARCH_COMPLETE")
        await _wait_for_ledger_row_by_state(case_id=case_id, to_state="COMPLIANCE_COMPLETE")

        with SessionLocal() as session:
            refreshed = session.get(PermitCase, case_id)
            assert refreshed is not None
            assert refreshed.case_state == "COMPLIANCE_COMPLETE"

            evaluations = (
                session.query(ComplianceEvaluation)
                .filter(ComplianceEvaluation.case_id == case_id)
                .all()
            )

        assert len(evaluations) == 1
        compliance_fixture = compliance_fixtures[0]
        compliance_row = evaluations[0]
        assert compliance_row.compliance_evaluation_id == compliance_fixture.compliance_evaluation_id
        assert compliance_row.schema_version == compliance_fixture.schema_version

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
            response = await api_client.get(
                f"/api/v1/cases/{case_id}/compliance",
                headers=headers,
            )
            assert response.status_code == 200
            body = response.json()

        assert body["case_id"] == case_id
        assert len(body["compliance_evaluations"]) == 1

        payload = body["compliance_evaluations"][0]
        assert payload["compliance_evaluation_id"] == compliance_fixture.compliance_evaluation_id
        assert payload["schema_version"] == compliance_fixture.schema_version
        assert payload["rule_results"] == [rule.model_dump() for rule in compliance_fixture.rule_results]
        assert payload["blockers"] == [issue.model_dump() for issue in compliance_fixture.blockers]
        assert payload["warnings"] == [issue.model_dump() for issue in compliance_fixture.warnings]
        assert payload["provenance"] == compliance_fixture.provenance
        assert payload["evidence_payload"] == compliance_fixture.evidence_payload

        response_evaluated = datetime.fromisoformat(payload["evaluated_at"])
        fixture_evaluated = compliance_fixture.evaluated_at
        if fixture_evaluated.tzinfo is None:
            fixture_evaluated = fixture_evaluated.replace(tzinfo=timezone.utc)
        assert response_evaluated == fixture_evaluated

        persist_compliance_evaluation(
            {"request_id": f"log-capture-{ulid.new()}", "case_id": case_id}
        )

        assert any(
            "compliance_activity.persisted" in message for message in activity_messages
        )
        assert any("cases.compliance_fetched" in message for message in api_messages)

    finally:
        activity_logger.removeHandler(activity_handler)
        activity_logger.setLevel(activity_level)
        activity_logger.disabled = activity_disabled
        activity_logger.propagate = activity_propagate
        api_logger.removeHandler(api_handler)
        api_logger.setLevel(api_level)
        api_logger.disabled = api_disabled
        api_logger.propagate = api_propagate

        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)


# ---------------------------------------------------------------------------
# Guard denial
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_compliance_guard_denial() -> None:
    _require_temporal_integration()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = f"CASE-COMP-DENIAL-{ulid.new()}"
    request_id = f"transition-{ulid.new()}"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-local",
                project_id=f"project-{case_id}",
                case_state=CaseState.RESEARCH_COMPLETE.value,
                review_state="PENDING",
                submission_mode="AUTOMATED",
                portal_support_level="FULLY_SUPPORTED",
                current_package_id=None,
                current_release_profile="default",
                legal_hold=False,
                closure_reason=None,
            )
        )
        session.commit()

    denial_result = apply_state_transition(
        StateTransitionRequest(
            request_id=request_id,
            case_id=case_id,
            from_state=CaseState.RESEARCH_COMPLETE,
            to_state=CaseState.COMPLIANCE_COMPLETE,
            actor_type=ActorType.system_guard,
            actor_id="system-guard",
            correlation_id=f"denial-{case_id}",
            causation_id=None,
            required_review_id=None,
            required_evidence_ids=[],
            override_id=None,
            requested_at=datetime.now(tz=timezone.utc),
            notes="force guard denial",
        )
    )

    assert denial_result.result == "denied"
    assert denial_result.event_type == "COMPLIANCE_REQUIRED_DENIED"

    with SessionLocal() as session:
        denial_row = session.get(CaseTransitionLedger, request_id)

    assert denial_row is not None
    assert denial_row.event_type == "COMPLIANCE_REQUIRED_DENIED"
