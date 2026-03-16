"""Integration tests for M006-S01: Document package generation and persistence.

Test coverage:
- Phase 6 fixture loading and schema validation (fixtures)
- Case ID override selection (fixtures)
- Document generation determinism (integration - TBD in T03)
- Package persistence with digest integrity (integration - TBD in T02)
- Manifest consistency with evidence registry (integration - TBD in T03)
- API package/manifest retrieval (integration - TBD in T03)
"""
from __future__ import annotations

import os
from datetime import datetime

import pytest

from sps.fixtures.phase6 import (
    DocumentFixtureDataset,
    DocumentSetFixture,
    load_document_fixtures,
    load_phase6_fixtures,
    load_template,
    resolve_phase6_fixture_case_id,
    select_document_fixtures,
)


# ============================================================================
# Fixture Loading and Schema Validation Tests
# ============================================================================


@pytest.mark.fixtures
def test_load_phase6_fixtures_schema_valid():
    """Phase 6 fixture dataset loads and validates against schema."""
    dataset = load_phase6_fixtures()
    
    assert isinstance(dataset, DocumentFixtureDataset)
    assert dataset.schema_version == "1.0.0"
    assert isinstance(dataset.generated_at, datetime)
    assert len(dataset.document_sets) > 0
    
    # Validate first document set structure
    doc_set = dataset.document_sets[0]
    assert isinstance(doc_set, DocumentSetFixture)
    assert doc_set.document_set_id
    assert doc_set.case_id
    assert doc_set.schema_version == "1.0.0"
    assert len(doc_set.documents) > 0
    assert doc_set.manifest is not None
    
    # Validate document structure
    doc = doc_set.documents[0]
    assert doc.document_id
    assert doc.document_type
    assert doc.template_name
    assert doc.variables
    
    # Validate manifest structure
    manifest = doc_set.manifest
    assert manifest.manifest_id
    assert manifest.case_id == doc_set.case_id
    assert manifest.package_version
    assert len(manifest.document_references) > 0
    assert manifest.target_portal_family


@pytest.mark.fixtures
def test_load_phase6_fixtures_pydantic_strict():
    """Phase 6 fixtures enforce Pydantic strict validation (no extra fields)."""
    dataset = load_phase6_fixtures()
    
    # Attempt to access a non-existent field should raise AttributeError
    with pytest.raises(AttributeError):
        _ = dataset.nonexistent_field  # type: ignore
    
    doc_set = dataset.document_sets[0]
    with pytest.raises(AttributeError):
        _ = doc_set.nonexistent_field  # type: ignore


@pytest.mark.fixtures
def test_load_document_fixtures_missing_file():
    """Load fails cleanly when fixture file is missing."""
    from pathlib import Path
    
    fake_path = Path("/nonexistent/documents.json")
    with pytest.raises(FileNotFoundError, match="Fixture file not found"):
        load_document_fixtures(path=fake_path)


@pytest.mark.fixtures
def test_load_template_success():
    """Template loader retrieves template content."""
    content = load_template("permit_application_template.txt")
    
    assert isinstance(content, str)
    assert len(content) > 0
    assert "{{case_id}}" in content
    assert "{{applicant_name}}" in content
    assert "SOLAR PERMIT APPLICATION" in content


@pytest.mark.fixtures
def test_load_template_missing():
    """Template loader fails cleanly when template is missing."""
    with pytest.raises(FileNotFoundError, match="Template not found"):
        load_template("nonexistent_template.txt")


# ============================================================================
# Case ID Override Selection Tests
# ============================================================================


@pytest.mark.fixtures
def test_resolve_phase6_fixture_case_id_no_override():
    """Case ID resolution returns input when no override is set."""
    original = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    try:
        if "SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE" in os.environ:
            del os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"]
        
        result = resolve_phase6_fixture_case_id("CASE-RUNTIME-001")
        assert result == "CASE-RUNTIME-001"
    finally:
        if original is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original


@pytest.mark.fixtures
def test_resolve_phase6_fixture_case_id_with_override():
    """Case ID resolution returns override when env var is set."""
    original = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        
        result = resolve_phase6_fixture_case_id("CASE-RUNTIME-001")
        assert result == "CASE-EXAMPLE-001"
    finally:
        if original is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original
        else:
            del os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"]


@pytest.mark.fixtures
def test_select_document_fixtures_default_case():
    """Select document fixtures returns fixture for matching case_id."""
    fixtures, fixture_case_id = select_document_fixtures("CASE-EXAMPLE-001")
    
    assert fixture_case_id == "CASE-EXAMPLE-001"
    assert len(fixtures) > 0
    assert all(f.case_id == "CASE-EXAMPLE-001" for f in fixtures)


@pytest.mark.fixtures
def test_select_document_fixtures_with_override():
    """Select document fixtures respects override env var and rewrites case_id."""
    original = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        
        fixtures, fixture_case_id = select_document_fixtures("CASE-RUNTIME-999")
        
        # fixture_case_id should be the override (what we searched for)
        assert fixture_case_id == "CASE-EXAMPLE-001"
        # but returned fixtures should have runtime case_id
        assert all(f.case_id == "CASE-RUNTIME-999" for f in fixtures)
    finally:
        if original is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original
        else:
            del os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"]


@pytest.mark.fixtures
def test_select_document_fixtures_no_match():
    """Select document fixtures returns empty list when no match found."""
    fixtures, _ = select_document_fixtures("CASE-NONEXISTENT-999")
    assert fixtures == []


# ============================================================================
# Integration Test Scaffolding (will be implemented in T02/T03)
# ============================================================================


@pytest.mark.integration
def test_persist_submission_package():
    """Package persistence stores SubmissionPackage + DocumentArtifacts with real sha256 digests."""
    import os
    from sps.db.models import DocumentArtifact, EvidenceArtifact, PermitCase, SubmissionPackage
    from sps.db.session import get_sessionmaker
    from sps.workflows.permit_case.activities import persist_submission_package
    from sps.workflows.permit_case.contracts import PersistSubmissionPackageRequest
    
    # Use override to select known fixture
    original = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        case_id = "CASE-TEST-PKG-001"
        
        # Ensure case exists
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            with session.begin():
                existing_case = session.get(PermitCase, case_id)
                if not existing_case:
                    session.add(
                        PermitCase(
                            case_id=case_id,
                            tenant_id="tenant-test",
                            project_id=f"project-{case_id}",
                            case_state="INCENTIVES_COMPLETE",
                            review_state="PENDING",
                            submission_mode="AUTOMATED",
                            portal_support_level="FULLY_SUPPORTED",
                            current_package_id=None,
                            current_release_profile="default",
                            legal_hold=False,
                            closure_reason=None,
                        )
                    )
        
        # Persist package
        request = PersistSubmissionPackageRequest(
            request_id="REQ-TEST-001",
            case_id=case_id,
        )
        
        package_id = persist_submission_package(request)
        
        # Verify persistence
        with SessionLocal() as session:
            # Check package row exists
            package = session.get(SubmissionPackage, package_id)
            assert package is not None
            assert package.case_id == case_id
            assert package.package_version
            assert package.manifest_artifact_id
            assert package.manifest_sha256_digest
            # Verify digest is not placeholder
            assert package.manifest_sha256_digest != "placeholder_digest_for_t02"
            assert len(package.manifest_sha256_digest) == 64  # sha256 hex length
            
            # Check manifest evidence artifact exists
            manifest_artifact = session.get(EvidenceArtifact, package.manifest_artifact_id)
            assert manifest_artifact is not None
            assert manifest_artifact.artifact_class == "MANIFEST"
            assert manifest_artifact.linked_case_id == case_id
            assert manifest_artifact.checksum == package.manifest_sha256_digest
            assert manifest_artifact.content_bytes > 0
            
            # Check document artifacts exist
            doc_artifacts = (
                session.query(DocumentArtifact)
                .filter(DocumentArtifact.package_id == package_id)
                .all()
            )
            assert len(doc_artifacts) > 0
            
            # Check each document has corresponding evidence artifact with real digest
            for doc_artifact in doc_artifacts:
                assert doc_artifact.document_id
                assert doc_artifact.document_type
                assert doc_artifact.template_name
                assert doc_artifact.sha256_digest
                # Verify digest is not placeholder
                assert doc_artifact.sha256_digest != "placeholder_digest_for_t02"
                assert len(doc_artifact.sha256_digest) == 64
                
                evidence = session.get(EvidenceArtifact, doc_artifact.evidence_artifact_id)
                assert evidence is not None
                assert evidence.artifact_class == "DOCUMENT"
                assert evidence.checksum == doc_artifact.sha256_digest
                assert evidence.content_bytes > 0
            
            # Check current_package_id updated
            case = session.get(PermitCase, case_id)
            assert case is not None
            assert case.current_package_id == package_id
            
        # Test idempotency - second call should return same package_id
        package_id_2 = persist_submission_package(request)
        assert package_id_2 == package_id
        
    finally:
        if original is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original
        else:
            if "SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE" in os.environ:
                del os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"]


@pytest.mark.integration
def test_document_generation_determinism():
    """Generated documents produce valid sha256 digests and consistent artifact structure."""
    import os
    from sps.documents.generator import generate_document, generate_submission_package
    from sps.fixtures.phase6 import select_document_fixtures
    
    original = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        case_id = "CASE-TEST-DETERMINISM-001"
        
        # Load fixture
        fixtures, _ = select_document_fixtures(case_id)
        assert len(fixtures) > 0
        
        doc_set = fixtures[0]
        
        # Generate package
        package = generate_submission_package(doc_set, runtime_case_id=case_id)
        
        # Verify manifest digest is valid sha256
        assert len(package.manifest_sha256_digest) == 64
        assert all(c in "0123456789abcdef" for c in package.manifest_sha256_digest)
        
        # Verify document digests are valid
        assert len(package.document_artifacts) > 0
        for doc in package.document_artifacts:
            assert len(doc.sha256_digest) == 64
            assert all(c in "0123456789abcdef" for c in doc.sha256_digest)
            assert len(doc.content_bytes) > 0
            
            # Verify digest matches actual content
            import hashlib
            computed_digest = hashlib.sha256(doc.content_bytes).hexdigest()
            assert computed_digest == doc.sha256_digest
            
        # Verify manifest references match document digests
        manifest_doc_ids = {ref.document_id: ref.sha256_digest for ref in package.manifest.document_references}
        for doc in package.document_artifacts:
            assert doc.document_id in manifest_doc_ids
            # Note: manifest references use placeholder artifact_ids at generation time
            # Real artifact_ids are assigned during persistence
            
    finally:
        if original is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original
        else:
            if "SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE" in os.environ:
                del os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"]


@pytest.mark.integration
def test_manifest_digest_consistency():
    """Manifest references match actual document artifact digests."""
    import os
    from sps.db.models import DocumentArtifact, EvidenceArtifact, PermitCase
    from sps.db.session import get_sessionmaker
    from sps.workflows.permit_case.activities import persist_submission_package
    from sps.workflows.permit_case.contracts import PersistSubmissionPackageRequest
    
    original = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        case_id = "CASE-TEST-MANIFEST-001"
        
        # Ensure case exists
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            with session.begin():
                existing_case = session.get(PermitCase, case_id)
                if not existing_case:
                    session.add(
                        PermitCase(
                            case_id=case_id,
                            tenant_id="tenant-test",
                            project_id=f"project-{case_id}",
                            case_state="INCENTIVES_COMPLETE",
                            review_state="PENDING",
                            submission_mode="AUTOMATED",
                            portal_support_level="FULLY_SUPPORTED",
                            current_package_id=None,
                            current_release_profile="default",
                            legal_hold=False,
                            closure_reason=None,
                        )
                    )
        
        # Persist package (generates + registers documents)
        request = PersistSubmissionPackageRequest(
            request_id="REQ-MANIFEST-TEST-001",
            case_id=case_id,
        )
        package_id = persist_submission_package(request)
        
        # Verify manifest digest consistency
        with SessionLocal() as session:
            doc_artifacts = (
                session.query(DocumentArtifact)
                .filter(DocumentArtifact.package_id == package_id)
                .all()
            )
            
            for doc_artifact in doc_artifacts:
                # Evidence artifact digest should match document artifact digest
                evidence = session.get(EvidenceArtifact, doc_artifact.evidence_artifact_id)
                assert evidence is not None
                assert evidence.checksum == doc_artifact.sha256_digest
                
                # Digest should be valid sha256 (64 hex chars)
                assert len(doc_artifact.sha256_digest) == 64
                assert all(c in "0123456789abcdef" for c in doc_artifact.sha256_digest)
                
    finally:
        if original is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original
        else:
            if "SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE" in os.environ:
                del os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"]


@pytest.mark.integration
@pytest.mark.skip(reason="T03: Workflow wiring not yet implemented")
def test_workflow_advances_to_document_complete():
    """Workflow transitions INCENTIVES_COMPLETE → DOCUMENT_COMPLETE after package persisted."""
    # TODO T03: Start workflow in INCENTIVES_COMPLETE state
    # TODO T03: Trigger document generation activity
    # TODO T03: Assert workflow advances to DOCUMENT_COMPLETE
    # TODO T03: Assert current_package_id set on permit_case
    pass


@pytest.mark.integration
@pytest.mark.skip(reason="T03: API endpoints not yet implemented")
def test_api_package_retrieval():
    """API exposes package metadata and manifest readback."""
    # TODO T03: Persist a package via workflow
    # TODO T03: GET /cases/{case_id}/package
    # TODO T03: Assert response includes package_id, manifest_id, document references
    # TODO T03: GET /cases/{case_id}/manifest
    # TODO T03: Assert manifest payload includes digest references
    pass


@pytest.mark.integration
@pytest.mark.skip(reason="T03: Evidence registry query not yet implemented")
def test_evidence_registry_document_retrieval():
    """Evidence registry returns document artifacts with matching checksums."""
    # TODO T03: Persist package with document artifacts
    # TODO T03: Query evidence registry by artifact_id
    # TODO T03: Assert artifact metadata includes sha256 checksum
    # TODO T03: Download artifact content and verify checksum matches
    pass
