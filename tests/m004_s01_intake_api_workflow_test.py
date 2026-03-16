"""M004 / S01 integration test: Intake API boundary.

Proves HTTP POST /api/v1/cases → Postgres PermitCase/Project rows → Temporal workflow
→ INTAKE_COMPLETE in case_transition_ledger.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run the Temporal-backed test.
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

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, PermitCase, Project
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
)
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client


# ---------------------------------------------------------------------------
# Helpers (mirrors m003_s01 pattern)
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
            sa.text("TRUNCATE TABLE case_transition_ledger, projects, permit_cases CASCADE")
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


def test_contract_validation_rejects_extra_fields() -> None:
    asyncio.run(_run_contract_validation())


def test_intake_flow_reaches_intake_complete() -> None:
    asyncio.run(_run_intake_flow())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_contract_validation() -> None:
    transport = httpx.ASGITransport(app=app)
    payload = {
        "tenant_id": "TEN-001",
        "intake_mode": "interactive",
        "project_description": "Install 500 kW rooftop solar.",
        "site_address": {
            "line1": "100 Example St",
            "city": "Helena",
            "state": "MT",
            "postal_code": "59601",
        },
        "requester": {"name": "Applicant Name", "email": "applicant@example.com"},
        "project_type": "commercial_solar",
        "system_size_kw": 500.0,
        "battery_flag": False,
        "service_upgrade_flag": False,
        "trenching_flag": False,
        "structural_modification_flag": False,
        "unexpected": "nope",
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/cases", json=payload)

    assert response.status_code == 422


async def _run_intake_flow() -> None:
    _require_temporal_integration()

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
        payload = {
            "tenant_id": "TEN-002",
            "intake_mode": "interactive",
            "project_description": "Install 12 kW rooftop solar on home.",
            "site_address": {
                "line1": "200 Example Ave",
                "city": "Bozeman",
                "state": "MT",
                "postal_code": "59715",
            },
            "requester": {"name": "Applicant Two", "email": "applicant2@example.com"},
            "project_type": "residential_solar",
            "system_size_kw": 12.0,
            "battery_flag": False,
            "service_upgrade_flag": False,
            "trenching_flag": False,
            "structural_modification_flag": False,
            "utility_name": "Example Utility",
        }

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
            response = await api_client.post("/api/v1/cases", json=payload)

        assert response.status_code == 201, (
            f"Expected 201 from intake API, got {response.status_code}: {response.text}"
        )
        body = response.json()
        case_id = body["case_id"]
        project_id = body["project_id"]

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            case_row = session.get(PermitCase, case_id)
            project_row = session.get(Project, project_id)

        assert case_row is not None
        assert project_row is not None
        assert case_row.project_id == project_id
        assert project_row.case_id == case_id
        assert project_row.project_type == "residential_solar"

        contact_metadata = project_row.contact_metadata or {}
        requester = contact_metadata.get("requester") or {}
        assert requester.get("name") == "Applicant Two"

        await _wait_for_ledger_row_by_event(
            case_id=case_id,
            event_type="CASE_STATE_CHANGED",
            to_state="INTAKE_COMPLETE",
            timeout_s=30.0,
        )

        with SessionLocal() as session:
            refreshed_case = session.get(PermitCase, case_id)

        assert refreshed_case is not None
        assert refreshed_case.case_state == "INTAKE_COMPLETE"

    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
