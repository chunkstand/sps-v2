from __future__ import annotations

import asyncio
import datetime as dt
import os
import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.db.models import ExternalStatusEvent, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.fixtures.phase7 import select_status_mapping_for_case
from sps.workflows.permit_case.activities import (
    deterministic_submission_adapter,
    persist_external_status_event,
    persist_submission_package,
)
from sps.workflows.permit_case.contracts import (
    ExternalStatusClass,
    ExternalStatusNormalizationRequest,
    PersistSubmissionPackageRequest,
    SubmissionAdapterRequest,
    submission_attempt_idempotency_key,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
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
                "TRUNCATE TABLE external_status_events, submission_attempts, "
                "submission_packages, evidence_artifacts, permit_cases CASCADE"
            )
        )


def _ensure_case(case_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        with session.begin():
            existing_case = session.get(PermitCase, case_id)
            if existing_case is None:
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-test",
                        project_id=f"project-{case_id}",
                        case_state="DOCUMENT_COMPLETE",
                        review_state="PENDING",
                        submission_mode="AUTOMATED",
                        portal_support_level="FULLY_SUPPORTED",
                        current_package_id=None,
                        current_release_profile="default",
                        legal_hold=False,
                        closure_reason=None,
                    )
                )


def _prepare_submission_attempt(*, case_id: str, request_suffix: str) -> str:
    _ensure_case(case_id)

    package_id = persist_submission_package(
        PersistSubmissionPackageRequest(
            request_id=f"REQ-PKG-{request_suffix}",
            case_id=case_id,
        )
    )

    submission_attempt_id = f"SUBATT-STATUS-{request_suffix}"
    request = SubmissionAdapterRequest(
        request_id=f"REQ-SUB-{request_suffix}",
        submission_attempt_id=submission_attempt_id,
        case_id=case_id,
        package_id=package_id,
        manifest_id="MANIFEST-001",
        target_portal_family="CITY_PORTAL_FAMILY_A",
        artifact_digests={},
        idempotency_key=submission_attempt_idempotency_key(case_id=case_id, attempt=1),
        attempt_number=1,
        correlation_id=f"corr-status-{request_suffix}",
    )

    result = deterministic_submission_adapter(request)
    return result.submission_attempt_id


def test_phase7_status_mapping_selection() -> None:
    original_override = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        case_id = "CASE-TEST-STATUS-001"

        selection, fixture_case_id = select_status_mapping_for_case(case_id)

        assert fixture_case_id == "CASE-EXAMPLE-001"
        assert selection.adapter_family == "CITY_PORTAL_FAMILY_A"
        assert selection.mapping_version == "2026-03-16.1"

        approved_mapping = selection.mappings["Approved"]
        assert approved_mapping.normalized_status == "APPROVAL_REPORTED"
    finally:
        if original_override is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_override
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)


def test_external_status_event_persistence_known_status() -> None:
    original_phase6 = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    original_phase7 = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"

        _wait_for_postgres_ready()
        _migrate_db()
        _reset_db()

        case_id = "CASE-TEST-STATUS-KNOWN"
        submission_attempt_id = _prepare_submission_attempt(case_id=case_id, request_suffix="KNOWN")
        received_at = dt.datetime(2026, 3, 16, 12, 0, tzinfo=dt.UTC)

        result = persist_external_status_event(
            ExternalStatusNormalizationRequest(
                event_id="ESE-TEST-KNOWN",
                case_id=case_id,
                submission_attempt_id=submission_attempt_id,
                raw_status="Approved",
                received_at=received_at,
            )
        )

        assert result.normalized_status == ExternalStatusClass.APPROVAL_REPORTED
        assert result.mapping_version == "2026-03-16.1"

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            row = session.get(ExternalStatusEvent, result.event_id)
            assert row is not None
            assert row.case_id == case_id
            assert row.submission_attempt_id == submission_attempt_id
            assert row.raw_status == "Approved"
            assert row.normalized_status == "APPROVAL_REPORTED"
            assert row.mapping_version == "2026-03-16.1"
    finally:
        if original_phase6 is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original_phase6
        else:
            os.environ.pop("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase7 is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_phase7
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)


def test_external_status_event_unknown_status_fails_closed() -> None:
    original_phase6 = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    original_phase7 = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"

        _wait_for_postgres_ready()
        _migrate_db()
        _reset_db()

        case_id = "CASE-TEST-STATUS-UNKNOWN"
        submission_attempt_id = _prepare_submission_attempt(case_id=case_id, request_suffix="UNKNOWN")

        with pytest.raises(ValueError):
            persist_external_status_event(
                ExternalStatusNormalizationRequest(
                    event_id="ESE-TEST-UNKNOWN",
                    case_id=case_id,
                    submission_attempt_id=submission_attempt_id,
                    raw_status="Totally New Status",
                )
            )

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            row = session.get(ExternalStatusEvent, "ESE-TEST-UNKNOWN")
            assert row is None
    finally:
        if original_phase6 is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original_phase6
        else:
            os.environ.pop("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase7 is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_phase7
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)


def test_external_status_api_list_readback() -> None:
    asyncio.run(_run_external_status_api_list_readback())


async def _run_external_status_api_list_readback() -> None:
    original_phase6 = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    original_phase7 = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"

        _wait_for_postgres_ready()
        _migrate_db()
        _reset_db()

        case_id = "CASE-TEST-STATUS-API"
        submission_attempt_id = _prepare_submission_attempt(case_id=case_id, request_suffix="API")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            ingest_response = await client.post(
                f"/api/v1/cases/{case_id}/external-status-events",
                json={
                    "submission_attempt_id": submission_attempt_id,
                    "raw_status": "Approved",
                },
            )

            assert ingest_response.status_code == 201, ingest_response.text
            body = ingest_response.json()
            assert body["normalized_status"] == "APPROVAL_REPORTED"

            list_response = await client.get(f"/api/v1/cases/{case_id}/external-status-events")
            assert list_response.status_code == 200, list_response.text
            list_body = list_response.json()
            events = list_body["external_status_events"]
            assert len(events) == 1
            assert events[0]["raw_status"] == "Approved"
            assert events[0]["mapping_version"] == "2026-03-16.1"
    finally:
        if original_phase6 is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original_phase6
        else:
            os.environ.pop("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase7 is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_phase7
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)
