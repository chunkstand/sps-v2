"""Seed minimal SubmissionPackage + EvidenceArtifact fixtures for integration tests.

Creates stub rows to satisfy SubmissionAttempt FK constraints during tests.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from sps.db.models import EvidenceArtifact, SubmissionAttempt, SubmissionPackage


def seed_submission_attempt(
    session: Session,
    case_id: str,
    submission_attempt_id: str,
    attempt_number: int = 1,
    status: str = "SUBMITTED",
) -> SubmissionAttempt:
    """Seed a minimal SubmissionAttempt with required EvidenceArtifact and SubmissionPackage.
    
    Returns:
        The created SubmissionAttempt object
    """
    artifact_id = f"ART-FIXTURE-{case_id}-{attempt_number}"
    package_id = f"PKG-FIXTURE-{case_id}-{attempt_number}"
    
    # Check if already exists
    existing_attempt = session.get(SubmissionAttempt, submission_attempt_id)
    if existing_attempt:
        return existing_attempt
    
    # Create EvidenceArtifact
    artifact = EvidenceArtifact(
        artifact_id=artifact_id,
        artifact_class="SUBMISSION_MANIFEST",
        storage_uri=f"s3://sps-evidence/FI/{artifact_id}/manifest.json",
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        content_bytes=100,
        content_type="application/json",
        authoritativeness="AUTHORITATIVE",
        retention_class="REGULATORY_MINIMUM",
        created_at=dt.datetime.now(dt.UTC),
    )
    session.add(artifact)
    
    # Create SubmissionPackage
    package = SubmissionPackage(
        package_id=package_id,
        case_id=case_id,
        package_version="1.0.0",
        manifest_artifact_id=artifact_id,
        manifest_sha256_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    session.add(package)
    session.flush()

    # Create SubmissionAttempt
    attempt = SubmissionAttempt(
        submission_attempt_id=submission_attempt_id,
        case_id=case_id,
        package_id=package_id,
        manifest_artifact_id=artifact_id,
        target_portal_family="CITY_PORTAL_FAMILY_A",
        portal_support_level="FULLY_SUPPORTED",
        request_id=f"REQ-{submission_attempt_id}",
        idempotency_key=f"IDEM-{submission_attempt_id}",
        attempt_number=attempt_number,
        status=status,
    )
    session.add(attempt)
    session.flush()
    
    return attempt
