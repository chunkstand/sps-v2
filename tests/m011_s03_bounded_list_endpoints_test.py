from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sps.api.main import app
from sps.api.routes import cases as cases_routes
from sps.api.routes import reviews as reviews_routes
from sps.config import get_settings
from sps.db.models import (
    ApprovalRecord,
    ComplianceEvaluation,
    CorrectionTask,
    EvidenceArtifact,
    ExternalStatusEvent,
    IncentiveAssessment,
    InspectionMilestone,
    JurisdictionResolution,
    ManualFallbackPackage,
    PermitCase,
    Project,
    RequirementSet,
    ResubmissionPackage,
    SubmissionAttempt,
    SubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker
from tests.helpers.auth_tokens import build_jwt

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("SPS_AUTH_JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET", "test-secret-0123456789abcdef0123456789")
    monkeypatch.setenv("SPS_AUTH_JWT_ALGORITHM", "HS256")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE inspection_milestones, approval_records, resubmission_packages, "
                "correction_tasks, manual_fallback_packages, external_status_events, "
                "submission_attempts, submission_packages, evidence_artifacts, "
                "incentive_assessments, compliance_evaluations, requirement_sets, "
                "jurisdiction_resolutions, projects, permit_cases CASCADE"
            )
        )


def _utc() -> dt.datetime:
    return dt.datetime(2026, 3, 18, 12, 0, tzinfo=dt.UTC)


def _intake_headers() -> dict[str, str]:
    token = build_jwt(subject="intake-user", roles=["intake"])
    return {"Authorization": f"Bearer {token}"}


def _reviewer_headers() -> dict[str, str]:
    token = build_jwt(subject="reviewer-user", roles=["reviewer"])
    return {"Authorization": f"Bearer {token}"}


def _seed_case(
    session: Session,
    *,
    case_id: str,
    created_at: dt.datetime,
    case_state: str = "DOCUMENT_COMPLETE",
) -> None:
    session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-test",
            project_id=f"PROJ-{case_id}",
            case_state=case_state,
            review_state="PENDING",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    session.flush()


def _seed_project(session: Session, *, case_id: str, created_at: dt.datetime) -> None:
    session.add(
        Project(
            project_id=f"PROJ-{case_id}",
            case_id=case_id,
            address=f"123 {case_id} Way",
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
            contact_metadata=None,
            created_at=created_at,
            updated_at=created_at,
        )
    )


def _seed_manifest_artifact(
    session: Session,
    *,
    case_id: str,
    artifact_id: str,
    created_at: dt.datetime,
) -> None:
    session.add(
        EvidenceArtifact(
            artifact_id=artifact_id,
            artifact_class="MANIFEST",
            producing_service="pytest",
            linked_case_id=case_id,
            linked_object_id=None,
            authoritativeness="AUTHORITATIVE",
            retention_class="CASE_CORE_7Y",
            checksum="a" * 64,
            storage_uri=f"s3://pytest/{artifact_id}.json",
            content_bytes=10,
            content_type="application/json",
            provenance={"source": "pytest"},
            created_at=created_at,
            expires_at=None,
            legal_hold_flag=False,
        )
    )
    session.flush()


def _seed_submission_package(
    session: Session,
    *,
    case_id: str,
    package_id: str,
    manifest_artifact_id: str,
    created_at: dt.datetime,
) -> None:
    session.add(
        SubmissionPackage(
            package_id=package_id,
            case_id=case_id,
            package_version="v1",
            manifest_artifact_id=manifest_artifact_id,
            manifest_sha256_digest="b" * 64,
            provenance={"source": "pytest"},
            created_at=created_at,
        )
    )
    session.flush()


def _seed_submission_attempt(
    session: Session,
    *,
    case_id: str,
    package_id: str,
    manifest_artifact_id: str,
    attempt_id: str,
    attempt_number: int,
    created_at: dt.datetime,
) -> None:
    session.add(
        SubmissionAttempt(
            submission_attempt_id=attempt_id,
            case_id=case_id,
            package_id=package_id,
            manifest_artifact_id=manifest_artifact_id,
            target_portal_family="CITY_PORTAL_FAMILY_A",
            portal_support_level="FULLY_SUPPORTED",
            request_id=f"REQ-{attempt_id}",
            idempotency_key=f"IDEMP-{attempt_id}",
            attempt_number=attempt_number,
            status="SUBMITTED",
            outcome="SUCCESS",
            external_tracking_id=None,
            receipt_artifact_id=None,
            submitted_at=created_at,
            failure_class=None,
            last_error=None,
            last_error_context=None,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    session.flush()


@dataclass(frozen=True)
class SurfaceConfig:
    name: str
    path_template: str
    response_key: str
    id_field: str
    default_limit: int
    max_limit: int
    headers_factory: Callable[[], dict[str, str]]
    seed_rows: Callable[[Session, str, int, dt.datetime], list[str]]


def _seed_jurisdictions(session: Session, case_id: str, total: int, created_at: dt.datetime) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    ids: list[str] = []
    for idx in range(total):
        row_id = f"JR-{idx:03d}"
        ids.append(row_id)
        session.add(
            JurisdictionResolution(
                jurisdiction_resolution_id=row_id,
                case_id=case_id,
                city_authority_id=f"CITY-{idx:03d}",
                county_authority_id=None,
                state_authority_id=None,
                utility_authority_id=None,
                zoning_district=None,
                overlays=[],
                permitting_portal_family="CITY_PORTAL_FAMILY_A",
                support_level="FULLY_SUPPORTED",
                manual_requirements=[],
                evidence_ids=[],
                provenance={"source": "pytest"},
                evidence_payload=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return sorted(ids, reverse=True)


def _seed_requirements(session: Session, case_id: str, total: int, created_at: dt.datetime) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    ids: list[str] = []
    for idx in range(total):
        row_id = f"REQSET-{idx:03d}"
        ids.append(row_id)
        session.add(
            RequirementSet(
                requirement_set_id=row_id,
                case_id=case_id,
                jurisdiction_ids=[],
                permit_types=["SOLAR"],
                forms_required=[],
                attachments_required=[],
                fee_rules=[],
                source_rankings=[],
                freshness_state="FRESH",
                freshness_expires_at=created_at + dt.timedelta(days=1),
                contradiction_state="CLEAR",
                evidence_ids=[],
                provenance={"source": "pytest"},
                evidence_payload=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return sorted(ids, reverse=True)


def _seed_compliance(session: Session, case_id: str, total: int, created_at: dt.datetime) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    ids: list[str] = []
    for idx in range(total):
        row_id = f"COMP-{idx:03d}"
        ids.append(row_id)
        session.add(
            ComplianceEvaluation(
                compliance_evaluation_id=row_id,
                case_id=case_id,
                schema_version="1.0.0",
                evaluated_at=created_at,
                rule_results=[],
                blockers=[],
                warnings=[],
                provenance={"source": "pytest"},
                evidence_payload=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return sorted(ids, reverse=True)


def _seed_incentives(session: Session, case_id: str, total: int, created_at: dt.datetime) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    ids: list[str] = []
    for idx in range(total):
        row_id = f"INC-{idx:03d}"
        ids.append(row_id)
        session.add(
            IncentiveAssessment(
                incentive_assessment_id=row_id,
                case_id=case_id,
                schema_version="1.0.0",
                assessed_at=created_at,
                candidate_programs=[],
                eligibility_status="ELIGIBLE",
                stacking_conflicts=[],
                deadlines=[],
                source_ids=[],
                advisory_value_range=None,
                authoritative_value_state="ADVISORY",
                provenance={"source": "pytest"},
                evidence_payload=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return sorted(ids, reverse=True)


def _seed_submission_attempts(
    session: Session, case_id: str, total: int, created_at: dt.datetime
) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    manifest_artifact_id = f"ART-MANIFEST-{case_id}"
    package_id = f"PKG-{case_id}"
    _seed_manifest_artifact(
        session, case_id=case_id, artifact_id=manifest_artifact_id, created_at=created_at
    )
    _seed_submission_package(
        session,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=manifest_artifact_id,
        created_at=created_at,
    )

    ids: list[str] = []
    for idx in range(total):
        attempt_id = f"SUBATT-{idx:03d}"
        ids.append(attempt_id)
        _seed_submission_attempt(
            session,
            case_id=case_id,
            package_id=package_id,
            manifest_artifact_id=manifest_artifact_id,
            attempt_id=attempt_id,
            attempt_number=idx + 1,
            created_at=created_at,
        )
    return sorted(ids, reverse=True)


def _seed_external_status_events(
    session: Session, case_id: str, total: int, created_at: dt.datetime
) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    manifest_artifact_id = f"ART-MANIFEST-{case_id}"
    package_id = f"PKG-{case_id}"
    attempt_id = f"SUBATT-{case_id}"
    _seed_manifest_artifact(
        session, case_id=case_id, artifact_id=manifest_artifact_id, created_at=created_at
    )
    _seed_submission_package(
        session,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=manifest_artifact_id,
        created_at=created_at,
    )
    _seed_submission_attempt(
        session,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=manifest_artifact_id,
        attempt_id=attempt_id,
        attempt_number=1,
        created_at=created_at,
    )

    ids: list[str] = []
    for idx in range(total):
        event_id = f"ESE-{idx:03d}"
        ids.append(event_id)
        session.add(
            ExternalStatusEvent(
                event_id=event_id,
                case_id=case_id,
                submission_attempt_id=attempt_id,
                raw_status="Approved",
                normalized_status="APPROVAL_REPORTED",
                confidence="HIGH",
                auto_advance_eligible=True,
                evidence_ids=[],
                mapping_version="2026-03-16.1",
                received_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return sorted(ids, reverse=True)


def _seed_manual_fallbacks(session: Session, case_id: str, total: int, created_at: dt.datetime) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    manifest_artifact_id = f"ART-MANIFEST-{case_id}"
    package_id = f"PKG-{case_id}"
    _seed_manifest_artifact(
        session, case_id=case_id, artifact_id=manifest_artifact_id, created_at=created_at
    )
    _seed_submission_package(
        session,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=manifest_artifact_id,
        created_at=created_at,
    )

    ids: list[str] = []
    for idx in range(total):
        row_id = f"MANFALL-{idx:03d}"
        ids.append(row_id)
        session.add(
            ManualFallbackPackage(
                manual_fallback_package_id=row_id,
                case_id=case_id,
                package_id=package_id,
                submission_attempt_id=None,
                package_version=f"v{idx + 1}",
                package_hash=f"HASH-{idx:03d}",
                reason="UNSUPPORTED_WORKFLOW",
                portal_support_level="MANUAL_REQUIRED",
                channel_type="EMAIL",
                proof_bundle_state="PENDING_REVIEW",
                required_attachments=[],
                operator_instructions=[],
                required_proof_types=[],
                escalation_owner=None,
                proof_bundle_artifact_id=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return sorted(ids, reverse=True)


def _seed_case_records(
    session: Session,
    case_id: str,
    total: int,
    created_at: dt.datetime,
    *,
    record_type: str,
) -> list[str]:
    _seed_case(session, case_id=case_id, created_at=created_at)
    manifest_artifact_id = f"ART-MANIFEST-{case_id}"
    package_id = f"PKG-{case_id}"
    attempt_id = f"SUBATT-{case_id}"
    _seed_manifest_artifact(
        session, case_id=case_id, artifact_id=manifest_artifact_id, created_at=created_at
    )
    _seed_submission_package(
        session,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=manifest_artifact_id,
        created_at=created_at,
    )
    _seed_submission_attempt(
        session,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=manifest_artifact_id,
        attempt_id=attempt_id,
        attempt_number=1,
        created_at=created_at,
    )

    ids: list[str] = []
    for idx in range(total):
        if record_type == "correction":
            row_id = f"CORR-{idx:03d}"
            session.add(
                CorrectionTask(
                    correction_task_id=row_id,
                    case_id=case_id,
                    submission_attempt_id=attempt_id,
                    status="OPEN",
                    summary="Need updated plans",
                    requested_at=created_at,
                    due_at=created_at + dt.timedelta(days=7),
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        elif record_type == "resubmission":
            row_id = f"RESUB-{idx:03d}"
            session.add(
                ResubmissionPackage(
                    resubmission_package_id=row_id,
                    case_id=case_id,
                    submission_attempt_id=attempt_id,
                    package_id=f"PKG-RESUB-{idx:03d}",
                    package_version=f"v{idx + 2}",
                    status="READY",
                    submitted_at=created_at,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        elif record_type == "approval":
            row_id = f"APR-{idx:03d}"
            session.add(
                ApprovalRecord(
                    approval_record_id=row_id,
                    case_id=case_id,
                    submission_attempt_id=attempt_id,
                    decision="APPROVED",
                    authority="city-review",
                    decided_at=created_at,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        elif record_type == "inspection":
            row_id = f"INSP-{idx:03d}"
            session.add(
                InspectionMilestone(
                    inspection_milestone_id=row_id,
                    case_id=case_id,
                    submission_attempt_id=attempt_id,
                    milestone_type="ROUGH_INSPECTION",
                    status="SCHEDULED",
                    scheduled_for=created_at + dt.timedelta(days=14),
                    completed_at=None,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        else:  # pragma: no cover
            raise AssertionError(f"unexpected record_type={record_type}")
        ids.append(row_id)

    return sorted(ids, reverse=True)


def _seed_review_queue(session: Session, _: str, total: int, created_at: dt.datetime) -> list[str]:
    ids: list[str] = []
    for idx in range(total):
        case_id = f"CASE-QUEUE-{idx:03d}"
        ids.append(case_id)
        _seed_case(
            session,
            case_id=case_id,
            created_at=created_at,
            case_state="REVIEW_PENDING",
        )
        _seed_project(session, case_id=case_id, created_at=created_at)
    return sorted(ids)


SURFACES = [
    SurfaceConfig(
        name="jurisdiction",
        path_template="/api/v1/cases/{case_id}/jurisdiction",
        response_key="jurisdictions",
        id_field="jurisdiction_resolution_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_jurisdictions,
    ),
    SurfaceConfig(
        name="requirements",
        path_template="/api/v1/cases/{case_id}/requirements",
        response_key="requirement_sets",
        id_field="requirement_set_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_requirements,
    ),
    SurfaceConfig(
        name="compliance",
        path_template="/api/v1/cases/{case_id}/compliance",
        response_key="compliance_evaluations",
        id_field="compliance_evaluation_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_compliance,
    ),
    SurfaceConfig(
        name="incentives",
        path_template="/api/v1/cases/{case_id}/incentives",
        response_key="incentive_assessments",
        id_field="incentive_assessment_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_incentives,
    ),
    SurfaceConfig(
        name="submission_attempts",
        path_template="/api/v1/cases/{case_id}/submission-attempts",
        response_key="submission_attempts",
        id_field="submission_attempt_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_submission_attempts,
    ),
    SurfaceConfig(
        name="external_status_events",
        path_template="/api/v1/cases/{case_id}/external-status-events",
        response_key="external_status_events",
        id_field="event_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_external_status_events,
    ),
    SurfaceConfig(
        name="manual_fallbacks",
        path_template="/api/v1/cases/{case_id}/manual-fallbacks",
        response_key="manual_fallback_packages",
        id_field="manual_fallback_package_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=_seed_manual_fallbacks,
    ),
    SurfaceConfig(
        name="correction_tasks",
        path_template="/api/v1/cases/{case_id}/correction-tasks",
        response_key="correction_tasks",
        id_field="correction_task_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=lambda session, case_id, total, created_at: _seed_case_records(
            session, case_id, total, created_at, record_type="correction"
        ),
    ),
    SurfaceConfig(
        name="resubmission_packages",
        path_template="/api/v1/cases/{case_id}/resubmission-packages",
        response_key="resubmission_packages",
        id_field="resubmission_package_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=lambda session, case_id, total, created_at: _seed_case_records(
            session, case_id, total, created_at, record_type="resubmission"
        ),
    ),
    SurfaceConfig(
        name="approval_records",
        path_template="/api/v1/cases/{case_id}/approval-records",
        response_key="approval_records",
        id_field="approval_record_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=lambda session, case_id, total, created_at: _seed_case_records(
            session, case_id, total, created_at, record_type="approval"
        ),
    ),
    SurfaceConfig(
        name="inspection_milestones",
        path_template="/api/v1/cases/{case_id}/inspection-milestones",
        response_key="inspection_milestones",
        id_field="inspection_milestone_id",
        default_limit=cases_routes._DEFAULT_LIST_LIMIT,
        max_limit=cases_routes._MAX_LIST_LIMIT,
        headers_factory=_intake_headers,
        seed_rows=lambda session, case_id, total, created_at: _seed_case_records(
            session, case_id, total, created_at, record_type="inspection"
        ),
    ),
    SurfaceConfig(
        name="review_queue",
        path_template="/api/v1/reviews/queue",
        response_key="cases",
        id_field="case_id",
        default_limit=reviews_routes._DEFAULT_QUEUE_LIMIT,
        max_limit=reviews_routes._MAX_QUEUE_LIMIT,
        headers_factory=_reviewer_headers,
        seed_rows=_seed_review_queue,
    ),
]


@pytest.mark.parametrize("surface", SURFACES, ids=[surface.name for surface in SURFACES])
def test_bounded_list_surfaces(surface: SurfaceConfig, auth_env: None) -> None:
    _reset_db()
    created_at = _utc()
    total_rows = surface.max_limit + 5
    case_id = f"CASE-LIMIT-{surface.name.upper()}"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        expected_ids = surface.seed_rows(session, case_id, total_rows, created_at)
        session.commit()

    client = TestClient(app)
    headers = surface.headers_factory()
    path = surface.path_template.format(case_id=case_id)

    default_response = client.get(path, headers=headers)
    assert default_response.status_code == 200, default_response.text
    default_items = default_response.json()[surface.response_key]
    default_ids = [item[surface.id_field] for item in default_items]
    assert default_ids == expected_ids[: surface.default_limit]

    requested_limit = 7
    honored_response = client.get(f"{path}?limit={requested_limit}", headers=headers)
    assert honored_response.status_code == 200, honored_response.text
    honored_items = honored_response.json()[surface.response_key]
    honored_ids = [item[surface.id_field] for item in honored_items]
    assert honored_ids == expected_ids[:requested_limit]

    oversized_response = client.get(
        f"{path}?limit={surface.max_limit + 50}",
        headers=headers,
    )
    assert oversized_response.status_code == 200, oversized_response.text
    oversized_items = oversized_response.json()[surface.response_key]
    oversized_ids = [item[surface.id_field] for item in oversized_items]
    assert oversized_ids == expected_ids[: surface.max_limit]

    repeated_response = client.get(
        f"{path}?limit={surface.max_limit + 50}",
        headers=headers,
    )
    assert repeated_response.status_code == 200, repeated_response.text
    repeated_items = repeated_response.json()[surface.response_key]
    repeated_ids = [item[surface.id_field] for item in repeated_items]
    assert repeated_ids == oversized_ids
