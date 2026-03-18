from __future__ import annotations

import asyncio
import datetime as dt
import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import (
    ApprovalRecord,
    CorrectionTask,
    InspectionMilestone,
    PermitCase,
    ResubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    deterministic_submission_adapter,
    persist_submission_package,
)
from sps.workflows.permit_case.contracts import (
    PersistSubmissionPackageRequest,
    SubmissionAdapterRequest,
    submission_attempt_idempotency_key,
)
from tests.helpers.auth_tokens import build_jwt

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
                "TRUNCATE TABLE inspection_milestones, approval_records, resubmission_packages, "
                "correction_tasks, external_status_events, submission_attempts, submission_packages, "
                "evidence_artifacts, permit_cases CASCADE"
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

    submission_attempt_id = f"SUBATT-POST-{request_suffix}"
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
        correlation_id=f"corr-post-{request_suffix}",
    )

    result = deterministic_submission_adapter(request)
    return result.submission_attempt_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_post_submission_artifact_api_lists() -> None:
    asyncio.run(_run_post_submission_artifact_api_lists())


async def _run_post_submission_artifact_api_lists() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    # Setup auth
    get_settings.cache_clear()
    import os
    os.environ["SPS_AUTH_JWT_ISSUER"] = "test-issuer"
    os.environ["SPS_AUTH_JWT_AUDIENCE"] = "test-audience"
    os.environ["SPS_AUTH_JWT_SECRET"] = "test-secret"
    os.environ["SPS_AUTH_JWT_ALGORITHM"] = "HS256"
    get_settings.cache_clear()
    
    token = build_jwt(subject="intake-user-1", roles=["intake"])
    headers = {"Authorization": f"Bearer {token}"}

    case_id = "CASE-EXAMPLE-001"  # Uses existing Phase 6 fixture
    submission_attempt_id = _prepare_submission_attempt(case_id=case_id, request_suffix="API")

    SessionLocal = get_sessionmaker()
    now = dt.datetime.now(dt.UTC)
    with SessionLocal() as session:
        with session.begin():
            session.add(
                CorrectionTask(
                    correction_task_id="CORR-001",
                    case_id=case_id,
                    submission_attempt_id=submission_attempt_id,
                    status="OPEN",
                    summary="Need updated plans",
                    requested_at=now,
                    due_at=now + dt.timedelta(days=7),
                )
            )
            session.add(
                ResubmissionPackage(
                    resubmission_package_id="RESUB-001",
                    case_id=case_id,
                    submission_attempt_id=submission_attempt_id,
                    package_id="PKG-RESUB-1",
                    package_version="v2",
                    status="READY",
                    submitted_at=now,
                )
            )
            session.add(
                ApprovalRecord(
                    approval_record_id="APR-001",
                    case_id=case_id,
                    submission_attempt_id=submission_attempt_id,
                    decision="APPROVED",
                    authority="city-review",
                    decided_at=now,
                )
            )
            session.add(
                InspectionMilestone(
                    inspection_milestone_id="INSP-001",
                    case_id=case_id,
                    submission_attempt_id=submission_attempt_id,
                    milestone_type="ROUGH_INSPECTION",
                    status="SCHEDULED",
                    scheduled_for=now + dt.timedelta(days=14),
                    completed_at=None,
                )
            )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        correction_response = await client.get(f"/api/v1/cases/{case_id}/correction-tasks", headers=headers)
        assert correction_response.status_code == 200, correction_response.text
        correction_body = correction_response.json()
        assert correction_body["case_id"] == case_id
        assert correction_body["correction_tasks"][0]["correction_task_id"] == "CORR-001"

        resubmission_response = await client.get(
            f"/api/v1/cases/{case_id}/resubmission-packages", headers=headers
        )
        assert resubmission_response.status_code == 200, resubmission_response.text
        resubmission_body = resubmission_response.json()
        assert resubmission_body["resubmission_packages"][0]["status"] == "READY"

        approval_response = await client.get(f"/api/v1/cases/{case_id}/approval-records", headers=headers)
        assert approval_response.status_code == 200, approval_response.text
        approval_body = approval_response.json()
        assert approval_body["approval_records"][0]["decision"] == "APPROVED"

        inspection_response = await client.get(
            f"/api/v1/cases/{case_id}/inspection-milestones", headers=headers
        )
        assert inspection_response.status_code == 200, inspection_response.text
        inspection_body = inspection_response.json()
        assert inspection_body["inspection_milestones"][0]["status"] == "SCHEDULED"
