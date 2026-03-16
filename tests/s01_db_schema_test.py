from __future__ import annotations

import datetime as dt

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError

from sps.db.models import (
    CaseTransitionLedger,
    ContradictionArtifact,
    EvidenceArtifact,
    ManualFallbackPackage,
    PermitCase,
    Project,
    ReleaseArtifact,
    ReleaseBundle,
    ReviewDecision,
    SubmissionAttempt,
    SubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    """Ensure migrations are applied for integration tests.

    This keeps the test runnable on a fresh docker volume without requiring
    a separate manual `alembic upgrade head` step.
    """

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def db_session():
    engine = get_engine()

    # Clear any prior data to keep tests repeatable.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                TRUNCATE TABLE
                  manual_fallback_packages,
                  submission_attempts,
                  document_artifacts,
                  submission_packages,
                  review_decisions,
                  contradiction_artifacts,
                  case_transition_ledger,
                  evidence_artifacts,
                  projects,
                  release_artifacts,
                  release_bundles,
                  permit_cases
                CASCADE;
                """
            )
        )

    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_submission_schema_smoke_insert_read(db_session):
    case_id = "CASE-2026-000123"
    project_id = "PROJ-001"

    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="TEN-001",
            project_id=project_id,
            case_state="INTAKE_PENDING",
            review_state="REVIEW_PENDING",
            submission_mode="interactive",
            portal_support_level="UNKNOWN",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )

    db_session.add(
        Project(
            project_id=project_id,
            case_id=case_id,
            address="100 Example St, Helena, MT 59601",
            parcel_id=None,
            project_type="rooftop_solar",
            system_size_kw=500.0,
            battery_flag=False,
            service_upgrade_flag=False,
            trenching_flag=False,
            structural_modification_flag=False,
            roof_type=None,
            occupancy_classification=None,
            utility_name=None,
            contact_metadata={"name": "Applicant Name"},
        )
    )

    # Ensure base rows are persisted before inserting FK-dependent rows.
    db_session.flush()

    db_session.add(
        ReviewDecision(
            decision_id="REV-001",
            schema_version="1.0",
            case_id=case_id,
            object_type="SubmissionPackage",
            object_id="PKG-004",
            decision_outcome="ACCEPT_WITH_DISSENT",
            reviewer_id="USR-REVIEW-01",
            reviewer_independence_status="PASS",
            evidence_ids=["ART-010"],
            contradiction_resolution="RESOLVED_WITH_HIGHER_RANK_SOURCE",
            dissent_flag=True,
            notes="ok",
            decision_at=_utcnow(),
            idempotency_key="idem-CASE-2026-000123-REV-001",
        )
    )

    db_session.add(
        ContradictionArtifact(
            contradiction_id="CON-001",
            case_id=case_id,
            scope="permit_requirement",
            source_a="official_city_form_page",
            source_b="official_city_fee_schedule_pdf",
            ranking_relation="same_rank",
            blocking_effect=True,
            resolution_status="OPEN",
        )
    )

    db_session.add(
        CaseTransitionLedger(
            transition_id="EVT-001",
            case_id=case_id,
            event_type="CASE_STATE_CHANGED",
            from_state=None,
            to_state="INTAKE_PENDING",
            actor_type="service",
            actor_id="orchestrator",
            correlation_id="CORR-001",
            occurred_at=_utcnow(),
            payload={"note": "seed"},
        )
    )

    db_session.add(
        EvidenceArtifact(
            artifact_id="ART-010",
            artifact_class="REQUIREMENT_EVIDENCE",
            producing_service="research-service",
            linked_case_id=case_id,
            linked_object_id="REQSET-002",
            authoritativeness="authoritative",
            retention_class="CASE_CORE_7Y",
            checksum="sha256:abc123",
            storage_uri="s3://evidence/ART-010.json",
            provenance={"producer": "research-service"},
            created_at=_utcnow(),
            expires_at=None,
            legal_hold_flag=False,
        )
    )

    db_session.add(
        EvidenceArtifact(
            artifact_id="ART-MAN-001",
            artifact_class="PACKAGE_MANIFEST",
            producing_service="packager",
            linked_case_id=case_id,
            linked_object_id="PKG-004",
            authoritativeness="authoritative",
            retention_class="CASE_CORE_7Y",
            checksum="sha256:manifest",
            storage_uri="s3://evidence/ART-MAN-001.json",
            provenance={"producer": "packager"},
            created_at=_utcnow(),
            expires_at=None,
            legal_hold_flag=False,
        )
    )

    db_session.add(
        EvidenceArtifact(
            artifact_id="ART-REC-001",
            artifact_class="SUBMISSION_RECEIPT",
            producing_service="submission-adapter",
            linked_case_id=case_id,
            linked_object_id="SUBATT-001",
            authoritativeness="authoritative",
            retention_class="CASE_CORE_7Y",
            checksum="sha256:receipt",
            storage_uri="s3://evidence/ART-REC-001.json",
            provenance={"producer": "submission-adapter"},
            created_at=_utcnow(),
            expires_at=None,
            legal_hold_flag=False,
        )
    )

    db_session.flush()

    db_session.add(
        SubmissionPackage(
            package_id="PKG-004",
            case_id=case_id,
            package_version="4",
            manifest_artifact_id="ART-MAN-001",
            manifest_sha256_digest="sha256:manifest",
            provenance={"source": "unit-test"},
        )
    )

    db_session.add(
        SubmissionAttempt(
            submission_attempt_id="SUBATT-001",
            case_id=case_id,
            package_id="PKG-004",
            manifest_artifact_id="ART-MAN-001",
            target_portal_family="CITY_PORTAL_FAMILY_A",
            portal_support_level="SUPPORTED",
            request_id="REQ-CASE-2026-000123-1",
            idempotency_key="submit-CASE-2026-000123-1",
            attempt_number=1,
            status="SUBMITTED",
            outcome="SUCCESS",
            external_tracking_id="HEL-PORTAL-9981",
            receipt_artifact_id="ART-REC-001",
            submitted_at=_utcnow(),
            failure_class=None,
            last_error=None,
            last_error_context=None,
        )
    )

    db_session.add(
        ManualFallbackPackage(
            manual_fallback_package_id="MFP-001",
            case_id=case_id,
            package_id="PKG-004",
            submission_attempt_id="SUBATT-001",
            package_version="4",
            package_hash="sha256:pkg",
            reason="UNSUPPORTED_PORTAL_WORKFLOW",
            portal_support_level="UNSUPPORTED",
            channel_type="official_authority_email",
            proof_bundle_state="PENDING_REVIEW",
            required_attachments=["ART-010"],
            operator_instructions=["Submit via email"],
            required_proof_types=["email_receipt"],
            escalation_owner="OPS-ONCALL",
            proof_bundle_artifact_id=None,
        )
    )

    db_session.add(
        ReleaseBundle(
            release_id="REL-001",
            spec_version="2.0.1",
            app_version="0.0.0",
            schema_version="1.0",
            model_version="2.0.1",
            policy_bundle_version="1.0",
            invariant_pack_version="1.0",
            adapter_versions={},
            artifact_digests={},
            approvals=[],
            created_at=_utcnow(),
        )
    )

    # Ensure parent row exists for FK.
    db_session.flush()

    db_session.add(
        ReleaseArtifact(
            artifact_id="ART-REL-001",
            release_id="REL-001",
            checksum="sha256:def456",
            storage_uri="s3://release/ART-REL-001.tgz",
            created_at=_utcnow(),
        )
    )

    db_session.commit()

    reloaded = db_session.get(PermitCase, case_id)
    assert reloaded is not None
    assert reloaded.project_id == project_id


def test_fk_violation_fails_closed(db_session):
    # Project references PermitCase via FK; inserting without a case should fail.
    db_session.add(
        Project(
            project_id="PROJ-NOCASE",
            case_id="CASE-DOES-NOT-EXIST",
            address="x",
            parcel_id=None,
            project_type="rooftop_solar",
            system_size_kw=1.0,
            battery_flag=False,
            service_upgrade_flag=False,
            trenching_flag=False,
            structural_modification_flag=False,
            roof_type=None,
            occupancy_classification=None,
            utility_name=None,
            contact_metadata=None,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
