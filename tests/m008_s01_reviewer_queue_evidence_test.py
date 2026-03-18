"""M008 / S01 integration tests: reviewer queue + evidence summary endpoints."""

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
from sps.api.routes import reviews as reviews_routes
from sps.config import get_settings
from sps.db.models import (
    EvidenceArtifact,
    ExternalStatusEvent,
    JurisdictionResolution,
    PermitCase,
    Project,
    RequirementSet,
    ReviewDecision,
    SubmissionAttempt,
    SubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers (self-contained for this slice)
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


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
                "TRUNCATE TABLE external_status_events, review_decisions, "
                "requirement_sets, jurisdiction_resolutions, evidence_artifacts, "
                "projects, permit_cases CASCADE"
            )
        )


def _seed_case_project(
    *,
    case_id: str,
    project_id: str,
    created_at: dt.datetime,
    case_state: str = "REVIEW_PENDING",
) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-test",
                project_id=project_id,
                case_state=case_state,
                review_state="PENDING",
                submission_mode="DIGITAL",
                portal_support_level="FULL",
                current_release_profile="default",
                legal_hold=False,
                created_at=created_at,
                updated_at=created_at,
            )
        )
        session.add(
            Project(
                project_id=project_id,
                case_id=case_id,
                address=f"123 {case_id} St",
                parcel_id=None,
                project_type="SOLAR",
                system_size_kw=7.2,
                battery_flag=False,
                service_upgrade_flag=False,
                trenching_flag=False,
                structural_modification_flag=False,
                roof_type=None,
                occupancy_classification=None,
                utility_name=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_reviewer_queue_empty_returns_empty_list() -> None:
    asyncio.run(_run_queue_empty_test())


def test_reviewer_queue_orders_review_pending_cases() -> None:
    messages: list[str] = []

    class _LoggerCapture:
        def info(self, msg: str, *args: object, **kwargs: object) -> None:
            messages.append(msg % args if args else msg)

        def warning(self, *args: object, **kwargs: object) -> None:
            return None

    original_logger = reviews_routes.logger
    reviews_routes.logger = _LoggerCapture()
    try:
        asyncio.run(_run_queue_ordering_test())
    finally:
        reviews_routes.logger = original_logger

    assert any("reviewer_api.queue_fetched" in msg for msg in messages)


def test_evidence_summary_aggregates_evidence_metadata() -> None:
    messages: list[str] = []

    class _LoggerCapture:
        def info(self, msg: str, *args: object, **kwargs: object) -> None:
            messages.append(msg % args if args else msg)

        def warning(self, *args: object, **kwargs: object) -> None:
            return None

    original_logger = reviews_routes.logger
    reviews_routes.logger = _LoggerCapture()
    try:
        asyncio.run(_run_evidence_summary_test())
    finally:
        reviews_routes.logger = original_logger

    assert any("reviewer_api.evidence_summary" in msg for msg in messages)


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_queue_empty_test() -> None:
    settings = get_settings()
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.get(
            "/api/v1/reviews/queue",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {"cases": []}


async def _run_queue_ordering_test() -> None:
    settings = get_settings()
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    first_ts = _utcnow() - dt.timedelta(hours=2)
    second_ts = _utcnow() - dt.timedelta(hours=1)

    _seed_case_project(case_id="CASE-001", project_id="PROJ-001", created_at=first_ts)
    _seed_case_project(case_id="CASE-002", project_id="PROJ-002", created_at=second_ts)
    _seed_case_project(
        case_id="CASE-ARCHIVE",
        project_id="PROJ-ARCHIVE",
        created_at=_utcnow(),
        case_state="SUBMITTED",
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.get(
            "/api/v1/reviews/queue",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
        )

    assert response.status_code == 200
    body = response.json()
    assert [case["case_id"] for case in body["cases"]] == ["CASE-001", "CASE-002"]
    assert body["cases"][0]["case_state"] == "REVIEW_PENDING"
    assert body["cases"][0]["project_type"] == "SOLAR"


async def _run_evidence_summary_test() -> None:
    settings = get_settings()
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-EVID-001"
    _seed_case_project(case_id=case_id, project_id="PROJ-EVID-001", created_at=_utcnow())

    evidence_ids = ["ART-001", "ART-002", "ART-003"]

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        for artifact_id in evidence_ids:
            session.add(
                EvidenceArtifact(
                    artifact_id=artifact_id,
                    artifact_class="REQUIREMENT_EVIDENCE",
                    producing_service="pytest",
                    linked_case_id=case_id,
                    linked_object_id=None,
                    authoritativeness="authoritative",
                    retention_class="CASE_CORE_7Y",
                    checksum="sha256:" + ("0" * 64),
                    storage_uri=f"s3://sps-evidence/evidence/{artifact_id}",
                    content_bytes=None,
                    content_type=None,
                    provenance={"source": "pytest"},
                    created_at=_utcnow(),
                    expires_at=None,
                    legal_hold_flag=False,
                )
            )

        session.add(
            SubmissionPackage(
                package_id="PKG-001",
                case_id=case_id,
                package_version="v1",
                manifest_artifact_id="ART-001",
                manifest_sha256_digest="sha256:" + ("0" * 64),
                provenance=None,
            )
        )
        session.flush()
        session.add(
            SubmissionAttempt(
                submission_attempt_id="ATTEMPT-001",
                case_id=case_id,
                package_id="PKG-001",
                manifest_artifact_id="ART-001",
                target_portal_family="PORTAL",
                portal_support_level="FULL",
                request_id="REQ-001",
                idempotency_key="idem/attempt-001",
                attempt_number=1,
                status="PENDING",
                outcome=None,
                external_tracking_id=None,
                receipt_artifact_id=None,
                submitted_at=None,
                failure_class=None,
                last_error=None,
                last_error_context=None,
            )
        )
        session.flush()
        session.add(
            ExternalStatusEvent(
                event_id="EVT-001",
                case_id=case_id,
                submission_attempt_id="ATTEMPT-001",
                raw_status="IN_REVIEW",
                normalized_status="IN_REVIEW",
                confidence="HIGH",
                auto_advance_eligible=False,
                evidence_ids=["ART-003"],
                mapping_version="v1",
                received_at=_utcnow(),
            )
        )
        session.add(
            JurisdictionResolution(
                jurisdiction_resolution_id="JR-001",
                case_id=case_id,
                support_level="FULL",
                evidence_ids=["ART-001", "ART-002"],
                provenance=None,
                evidence_payload=None,
            )
        )
        session.add(
            RequirementSet(
                requirement_set_id="RS-001",
                case_id=case_id,
                jurisdiction_ids=["J-001"],
                permit_types=["SOLAR"],
                forms_required=["FORM-A"],
                attachments_required=["ATT-1"],
                fee_rules=None,
                source_rankings=[{"source": "test", "rank": 1}],
                freshness_state="FRESH",
                freshness_expires_at=_utcnow() + dt.timedelta(days=30),
                contradiction_state="NONE",
                evidence_ids=["ART-002", "ART-003"],
                provenance=None,
                evidence_payload=None,
            )
        )
        session.add(
            ReviewDecision(
                decision_id="DEC-001",
                schema_version="1.0",
                case_id=case_id,
                object_type="permit_case",
                object_id=case_id,
                decision_outcome="ACCEPT",
                reviewer_id="reviewer-001",
                reviewer_independence_status="PASS",
                evidence_ids=["ART-001"],
                contradiction_resolution=None,
                dissent_flag=False,
                notes=None,
                decision_at=_utcnow(),
                idempotency_key="idem/dec-001",
            )
        )
        session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.get(
            f"/api/v1/reviews/cases/{case_id}/evidence-summary",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["case_id"] == case_id
    assert body["evidence_count"] == 3
    assert body["artifact_count"] == 3
    assert body["review_decision_count"] == 1
    assert body["evidence_ids"] == sorted(evidence_ids)
    assert {artifact["artifact_id"] for artifact in body["artifacts"]} == set(evidence_ids)
    assert body["review_decisions"][0]["reviewer_independence_status"] == "PASS"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/reviews/queue",
        "/api/v1/reviews/cases/CASE-404/evidence-summary",
    ],
)
def test_reviewer_endpoints_require_api_key(path: str) -> None:
    asyncio.run(_run_auth_failure_test(path))


async def _run_auth_failure_test(path: str) -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.get(path)

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["error"] in {"missing_api_key", "invalid_api_key"}
