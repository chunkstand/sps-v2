"""M004 / S02 fixtures + workflow progression tests.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run the Temporal-backed test.
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
from sps.db.models import (
    CaseTransitionLedger,
    JurisdictionResolution,
    PermitCase,
    RequirementSet,
)
from sps.db.session import get_engine, get_sessionmaker
from sps.fixtures.phase4 import load_jurisdiction_fixtures, load_requirement_fixtures
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_jurisdiction_resolutions,
    persist_requirement_sets,
)
from sps.workflows.permit_case.contracts import (
    ActorType,
    CaseState,
    PermitCaseWorkflowResult,
    StateTransitionRequest,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client


# ---------------------------------------------------------------------------
# Fixtures schema validation
# ---------------------------------------------------------------------------


def test_phase4_fixture_schema_loads() -> None:
    jurisdiction_dataset = load_jurisdiction_fixtures()
    requirement_dataset = load_requirement_fixtures()

    assert jurisdiction_dataset.jurisdictions, "jurisdiction fixtures should not be empty"
    assert requirement_dataset.requirement_sets, "requirement fixtures should not be empty"

    jurisdiction = jurisdiction_dataset.jurisdictions[0]
    requirement_set = requirement_dataset.requirement_sets[0]

    assert jurisdiction.support_level is not None
    assert jurisdiction.evidence_ids

    assert requirement_set.freshness_state is not None
    assert requirement_set.contradiction_state is not None
    assert requirement_set.source_rankings
    assert isinstance(requirement_set.freshness_expires_at, datetime)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
                "TRUNCATE TABLE case_transition_ledger, jurisdiction_resolutions, "
                "requirement_sets, projects, permit_cases CASCADE"
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


# ---------------------------------------------------------------------------
# Integration: workflow progression
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_workflow_progression(caplog: pytest.LogCaptureFixture) -> None:
    _require_temporal_integration()

    caplog.set_level(logging.INFO)
    asyncio.run(_run_workflow_progression(caplog))


async def _run_workflow_progression(caplog: pytest.LogCaptureFixture) -> None:
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
            persist_jurisdiction_resolutions,
            persist_requirement_sets,
            apply_state_transition,
        ],
        activity_executor=executor,
    )
    worker_task = asyncio.create_task(worker.run())

    try:
        jurisdiction_dataset = load_jurisdiction_fixtures()
        requirement_dataset = load_requirement_fixtures()
        case_id = jurisdiction_dataset.jurisdictions[0].case_id
        assert case_id == requirement_dataset.requirement_sets[0].case_id

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

        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            {"case_id": case_id},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        raw_result = await asyncio.wait_for(handle.result(), timeout=30.0)
        result = (
            raw_result
            if isinstance(raw_result, PermitCaseWorkflowResult)
            else PermitCaseWorkflowResult.model_validate(raw_result)
        )

        assert result.case_id == case_id
        assert result.final_result.result == "applied"
        assert result.final_result.event_type == "CASE_STATE_CHANGED"

        await _wait_for_ledger_row_by_state(case_id=case_id, to_state="JURISDICTION_COMPLETE")
        await _wait_for_ledger_row_by_state(case_id=case_id, to_state="RESEARCH_COMPLETE")

        with SessionLocal() as session:
            refreshed = session.get(PermitCase, case_id)
            assert refreshed is not None
            assert refreshed.case_state == "RESEARCH_COMPLETE"

            jurisdictions = (
                session.query(JurisdictionResolution)
                .filter(JurisdictionResolution.case_id == case_id)
                .all()
            )
            requirements = (
                session.query(RequirementSet)
                .filter(RequirementSet.case_id == case_id)
                .all()
            )

        assert len(jurisdictions) == 1
        assert len(requirements) == 1

        jurisdiction_fixture = jurisdiction_dataset.jurisdictions[0]
        requirement_fixture = requirement_dataset.requirement_sets[0]

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
            jurisdiction_response = await api_client.get(f"/api/v1/cases/{case_id}/jurisdiction")
            assert jurisdiction_response.status_code == 200
            jurisdiction_body = jurisdiction_response.json()

            requirements_response = await api_client.get(f"/api/v1/cases/{case_id}/requirements")
            assert requirements_response.status_code == 200
            requirements_body = requirements_response.json()

        assert jurisdiction_body["case_id"] == case_id
        assert len(jurisdiction_body["jurisdictions"]) == 1

        jurisdiction_payload = jurisdiction_body["jurisdictions"][0]
        assert jurisdiction_payload["jurisdiction_resolution_id"] == jurisdiction_fixture.jurisdiction_resolution_id
        assert jurisdiction_payload["support_level"] == jurisdiction_fixture.support_level.value
        assert jurisdiction_payload["evidence_ids"] == jurisdiction_fixture.evidence_ids
        assert jurisdiction_payload["provenance"] == jurisdiction_fixture.provenance
        assert jurisdiction_payload["evidence_payload"] == jurisdiction_fixture.evidence_payload

        assert requirements_body["case_id"] == case_id
        assert len(requirements_body["requirement_sets"]) == 1

        requirements_payload = requirements_body["requirement_sets"][0]
        assert requirements_payload["requirement_set_id"] == requirement_fixture.requirement_set_id
        assert requirements_payload["freshness_state"] == requirement_fixture.freshness_state.value
        assert requirements_payload["evidence_ids"] == requirement_fixture.evidence_ids
        assert requirements_payload["provenance"] == requirement_fixture.provenance
        assert requirements_payload["evidence_payload"] == requirement_fixture.evidence_payload

        response_freshness = datetime.fromisoformat(requirements_payload["freshness_expires_at"])
        fixture_freshness = requirement_fixture.freshness_expires_at
        if fixture_freshness.tzinfo is None:
            fixture_freshness = fixture_freshness.replace(tzinfo=timezone.utc)
        assert response_freshness == fixture_freshness

        denial_case_id = f"CASE-DENIAL-{ulid.new()}"
        denial_request_id = f"transition-{ulid.new()}"

        with SessionLocal() as session:
            session.add(
                PermitCase(
                    case_id=denial_case_id,
                    tenant_id="tenant-local",
                    project_id=f"project-{denial_case_id}",
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

        denial_result = apply_state_transition(
            StateTransitionRequest(
                request_id=denial_request_id,
                case_id=denial_case_id,
                from_state=CaseState.INTAKE_COMPLETE,
                to_state=CaseState.JURISDICTION_COMPLETE,
                actor_type=ActorType.system_guard,
                actor_id="system-guard",
                correlation_id=f"denial-{denial_case_id}",
                causation_id=None,
                required_review_id=None,
                required_evidence_ids=[],
                override_id=None,
                requested_at=datetime.now(tz=timezone.utc),
                notes="force guard denial",
            )
        )
        assert denial_result.result == "denied"
        assert denial_result.event_type == "JURISDICTION_REQUIRED_DENIED"

        with SessionLocal() as session:
            denial_row = session.get(CaseTransitionLedger, denial_request_id)

        assert denial_row is not None
        assert denial_row.event_type == "JURISDICTION_REQUIRED_DENIED"

        messages = [record.getMessage() for record in caplog.records]
        assert any("jurisdiction_activity.persisted" in message for message in messages)
        assert any("requirements_activity.persisted" in message for message in messages)
        assert any("workflow.transition_applied" in message for message in messages)
        assert any("cases.jurisdiction_fetched" in message for message in messages)
        assert any("cases.requirements_fetched" in message for message in messages)

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
