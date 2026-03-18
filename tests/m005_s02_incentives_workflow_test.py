"""M005 / S02 incentive fixture + workflow tests.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run Temporal-backed tests.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import sqlalchemy as sa
import ulid
from alembic import command
from alembic.config import Config
from temporalio.worker import Worker

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, IncentiveAssessment, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.fixtures.phase5 import (
    PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV,
    load_incentive_fixtures,
    select_incentive_fixtures,
)
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_incentive_assessment,
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


def test_incentive_fixtures_schema_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset = load_incentive_fixtures()

    assert dataset.assessments, "incentive fixtures should not be empty"

    assessment = dataset.assessments[0]
    assert assessment.schema_version
    assert isinstance(assessment.assessed_at, datetime)
    assert assessment.candidate_programs
    assert assessment.source_ids
    assert assessment.authoritative_value_state
    assert assessment.provenance is not None

    program = assessment.candidate_programs[0]
    assert program.program_id
    assert program.program_name
    assert program.source_id
    assert program.provenance is not None
    assert program.evidence_payload is not None

    deadline = assessment.deadlines[0]
    assert deadline.deadline_id
    assert deadline.source_id
    assert deadline.provenance is not None

    runtime_case_id = f"CASE-INC-OVERRIDE-{ulid.new()}"
    monkeypatch.setenv(PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV, assessment.case_id)

    fixtures, fixture_case_id = select_incentive_fixtures(runtime_case_id)
    assert fixture_case_id == assessment.case_id
    assert fixtures, "override selection should return fixtures"
    assert fixtures[0].case_id == runtime_case_id


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
                "TRUNCATE TABLE incentive_assessments, compliance_evaluations, "
                "case_transition_ledger, jurisdiction_resolutions, requirement_sets, "
                "projects, permit_cases CASCADE"
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
def _configure_phase5_fixture_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV, "CASE-EXAMPLE-001")


async def _wait_for_ledger_event_type(
    *, case_id: str, event_type: str, timeout_s: float = 30.0
) -> CaseTransitionLedger:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            row = (
                session.query(CaseTransitionLedger)
                .filter(
                    CaseTransitionLedger.case_id == case_id,
                    CaseTransitionLedger.event_type == event_type,
                )
                .first()
            )
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise RuntimeError(f"ledger row not found for case_id={case_id} event_type={event_type}")


# ---------------------------------------------------------------------------
# Persistence activity
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_incentive_persistence_activity_idempotent() -> None:
    _require_temporal_integration()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = f"CASE-INC-PERSIST-{ulid.new()}"
    fixtures, fixture_case_id = select_incentive_fixtures(case_id)
    assert fixture_case_id == "CASE-EXAMPLE-001"
    assessment = fixtures[0]

    activity_messages, logger, handler, old_level, old_disabled, old_propagate = _capture_logger(
        "sps.workflows.permit_case.activities_impl"
    )

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-local",
                project_id=f"project-{case_id}",
                case_state=CaseState.COMPLIANCE_COMPLETE.value,
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

    try:
        request_id = f"incentive-persist-{ulid.new()}"
        created_ids = persist_incentive_assessment({"request_id": request_id, "case_id": case_id})
        assert created_ids == [assessment.incentive_assessment_id]

        with SessionLocal() as session:
            rows = (
                session.query(IncentiveAssessment)
                .filter(IncentiveAssessment.case_id == case_id)
                .all()
            )
        assert len(rows) == 1

        row = rows[0]
        assert row.incentive_assessment_id == assessment.incentive_assessment_id
        assert row.schema_version == assessment.schema_version
        assert row.eligibility_status == assessment.eligibility_status
        assert row.candidate_programs == [
            program.model_dump(mode="json") for program in assessment.candidate_programs
        ]
        assert row.authoritative_value_state == assessment.authoritative_value_state
        assert row.provenance == assessment.provenance
        assert row.evidence_payload == assessment.evidence_payload

        persisted_at = row.assessed_at
        fixture_assessed = assessment.assessed_at
        if fixture_assessed.tzinfo is None:
            fixture_assessed = fixture_assessed.replace(tzinfo=timezone.utc)
        assert persisted_at == fixture_assessed

        persist_incentive_assessment({"request_id": f"repeat-{ulid.new()}", "case_id": case_id})

        with SessionLocal() as session:
            rows = (
                session.query(IncentiveAssessment)
                .filter(IncentiveAssessment.case_id == case_id)
                .all()
            )
        assert len(rows) == 1
        assert any("incentives_activity.persisted" in message for message in activity_messages)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        logger.disabled = old_disabled
        logger.propagate = old_propagate


# ---------------------------------------------------------------------------
# Integration: workflow progression + API
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_workflow_progression(caplog: pytest.LogCaptureFixture) -> None:
    _require_temporal_integration()

    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, logger="sps.workflows.permit_case.activities_impl")
    caplog.set_level(logging.INFO, logger="sps.api.routes.cases_impl")
    asyncio.run(_run_workflow_progression())


async def _run_workflow_progression() -> None:
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
            persist_incentive_assessment,
            apply_state_transition,
        ],
        activity_executor=executor,
    )
    worker_task = asyncio.create_task(worker.run())

    try:
        case_id = f"CASE-INC-{ulid.new()}"
        incentive_fixtures, fixture_case_id = select_incentive_fixtures(case_id)
        assert fixture_case_id == "CASE-EXAMPLE-001"

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            session.add(
                PermitCase(
                    case_id=case_id,
                    tenant_id="tenant-local",
                    project_id=f"project-{case_id}",
                    case_state=CaseState.COMPLIANCE_COMPLETE.value,
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

        await _wait_for_ledger_event_type(
            case_id=case_id,
            event_type="INCENTIVES_FRESHNESS_DENIED",
        )

        with SessionLocal() as session:
            refreshed = session.get(PermitCase, case_id)
            assert refreshed is not None
            assert refreshed.case_state == "COMPLIANCE_COMPLETE"

            assessments = (
                session.query(IncentiveAssessment)
                .filter(IncentiveAssessment.case_id == case_id)
                .all()
            )

        assert len(assessments) == 1
        assessment_fixture = incentive_fixtures[0]
        assessment_row = assessments[0]
        assert assessment_row.incentive_assessment_id == assessment_fixture.incentive_assessment_id
        assert assessment_row.schema_version == assessment_fixture.schema_version
        assert assessment_row.eligibility_status == assessment_fixture.eligibility_status

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
            response = await api_client.get(
                f"/api/v1/cases/{case_id}/incentives",
                headers=headers,
            )
            assert response.status_code == 200
            body = response.json()

        assert body["case_id"] == case_id
        assert len(body["incentive_assessments"]) == 1

        payload = body["incentive_assessments"][0]
        assert payload["incentive_assessment_id"] == assessment_fixture.incentive_assessment_id
        assert payload["schema_version"] == assessment_fixture.schema_version
        assert payload["eligibility_status"] == assessment_fixture.eligibility_status
        assert payload["candidate_programs"] == [
            program.model_dump(mode="json")
            for program in assessment_fixture.candidate_programs
        ]
        assert payload["stacking_conflicts"] == assessment_fixture.stacking_conflicts
        assert payload["deadlines"] == [
            deadline.model_dump(mode="json") for deadline in assessment_fixture.deadlines
        ]
        assert payload["source_ids"] == assessment_fixture.source_ids
        assert payload["advisory_value_range"] == assessment_fixture.advisory_value_range
        assert payload["authoritative_value_state"] == assessment_fixture.authoritative_value_state
        assert payload["provenance"] == assessment_fixture.provenance
        assert payload["evidence_payload"] == assessment_fixture.evidence_payload

        response_assessed = datetime.fromisoformat(payload["assessed_at"])
        fixture_assessed = assessment_fixture.assessed_at
        if fixture_assessed.tzinfo is None:
            fixture_assessed = fixture_assessed.replace(tzinfo=timezone.utc)
        assert response_assessed == fixture_assessed

        assert any("incentives_activity.persisted" in message for message in activity_messages)
        assert any("cases.incentives_fetched" in message for message in api_messages)
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
def test_incentive_guard_denial() -> None:
    _require_temporal_integration()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    dataset = load_incentive_fixtures()
    assessment = dataset.assessments[0]

    case_id = f"CASE-INC-DENIAL-{ulid.new()}"
    request_id = f"transition-{ulid.new()}"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-local",
                project_id=f"project-{case_id}",
                case_state=CaseState.COMPLIANCE_COMPLETE.value,
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

        session.add(
            IncentiveAssessment(
                incentive_assessment_id=assessment.incentive_assessment_id,
                case_id=case_id,
                schema_version=assessment.schema_version,
                assessed_at=datetime.now(tz=timezone.utc) - timedelta(days=5),
                candidate_programs=[
                    program.model_dump(mode="json") for program in assessment.candidate_programs
                ],
                eligibility_status=assessment.eligibility_status,
                stacking_conflicts=assessment.stacking_conflicts,
                deadlines=[
                    deadline.model_dump(mode="json") for deadline in assessment.deadlines
                ],
                source_ids=assessment.source_ids,
                advisory_value_range=assessment.advisory_value_range,
                authoritative_value_state=assessment.authoritative_value_state,
                provenance=assessment.provenance,
                evidence_payload=assessment.evidence_payload,
            )
        )
        session.commit()

    denial_result = apply_state_transition(
        StateTransitionRequest(
            request_id=request_id,
            case_id=case_id,
            from_state=CaseState.COMPLIANCE_COMPLETE,
            to_state=CaseState.INCENTIVES_COMPLETE,
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
    assert denial_result.event_type == "INCENTIVES_FRESHNESS_DENIED"
    assert denial_result.guard_assertion_id == "INV-SPS-INC-001"

    with SessionLocal() as session:
        denial_row = session.get(CaseTransitionLedger, request_id)

    assert denial_row is not None
    assert denial_row.event_type == "INCENTIVES_FRESHNESS_DENIED"
