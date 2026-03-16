---
id: T02
parent: S01
milestone: M006-h7v2qk
provides:
  - SubmissionPackage and DocumentArtifact schema with migration applied
  - Evidence registry helper for sha256-validated document/manifest storage
  - persist_submission_package activity with transactional package persistence
key_files:
  - src/sps/db/models.py
  - alembic/versions/a1b2c3d4e5f6_submission_packages.py
  - src/sps/documents/registry.py
  - src/sps/workflows/permit_case/activities.py
key_decisions:
  - Used explicit session.flush() calls to enforce foreign key ordering (manifest evidence → package → document evidence → document artifacts)
  - Activity persistence uses placeholder digests for T02; real sha256 digests will come from registry in T03
patterns_established:
  - Evidence registry provides register_document() and register_manifest() with sha256 validation
  - Package persistence activity follows Phase 4/5 idempotency pattern with IntegrityError handling
observability_surfaces:
  - activity.start/ok/error logs with case_id, package_id, request_id
  - package_activity.persisted log with manifest_id, doc_count
  - DB tables: submission_packages, document_artifacts, evidence_artifacts
  - permit_cases.current_package_id updated after successful package persistence
duration: 45m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Persist submission packages and evidence artifacts

**Package persistence activity stores SubmissionPackage + DocumentArtifact rows with evidence linkage and updates permit_cases.current_package_id in a single transaction.**

## What Happened

Implemented the database schema, evidence registry, and persistence activity for submission packages:

1. **Schema & migration**: Added SubmissionPackage and DocumentArtifact models with foreign keys to evidence_artifacts. Migration creates both tables with proper indexes and constraints.

2. **Evidence registry**: Implemented `EvidenceRegistry` helper in `src/sps/documents/registry.py` with `register_document()` and `register_manifest()` methods. Each computes sha256 digest, uploads to S3 with integrity checks, and returns `RegisteredArtifact` with artifact_id + digest + storage_uri.

3. **Persistence activity**: Added `persist_submission_package` activity that:
   - Loads fixture document set for the case_id (T03 will accept generated payload)
   - Creates manifest evidence artifact with placeholder digest
   - Creates SubmissionPackage row linked to manifest artifact
   - Creates document evidence artifacts for each document
   - Creates DocumentArtifact rows linking package → evidence
   - Updates permit_cases.current_package_id
   - All in single transaction with explicit flush() calls to satisfy foreign key ordering

4. **Test coverage**: Removed skip marker from `test_persist_submission_package` and implemented full persistence verification:
   - Asserts package row created with manifest reference
   - Asserts manifest evidence artifact persisted with correct class + checksum
   - Asserts document artifacts linked to package with evidence artifacts
   - Asserts current_package_id updated on permit_case
   - Verifies idempotency (second call returns same package_id)

**Key implementation detail**: Added explicit `session.flush()` calls after each foreign-key-dependent group (manifest evidence → package → document evidence → document artifacts) to ensure SQLAlchemy respects insertion order within the transaction.

## Verification

```bash
# Migration applied successfully
alembic upgrade head
# INFO  [alembic.runtime.migration] Running upgrade 9b7a3d2c1f0e -> a1b2c3d4e5f6, submission_packages

# Persistence test passes
pytest tests/m006_s01_document_package_test.py::test_persist_submission_package -v
# PASSED

# All fixture tests still pass
pytest tests/m006_s01_document_package_test.py -k fixtures -v
# 10 passed
```

Test verifies:
- SubmissionPackage row persisted with manifest_artifact_id and digest
- Manifest EvidenceArtifact created with MANIFEST class
- DocumentArtifact rows linked to package
- Document EvidenceArtifact rows created with DOCUMENT class
- permit_cases.current_package_id updated
- Idempotency (second persist returns same package_id)

## Diagnostics

**Activity logs:**
```
activity.start name=persist_submission_package workflow_id=... case_id=... request_id=...
activity.lookup name=persist_submission_package fixture_case_id=... override=...
package_activity.persisted case_id=... package_id=... manifest_id=... doc_count=...
activity.ok name=persist_submission_package package_id=...
```

**DB inspection:**
```sql
SELECT package_id, case_id, manifest_artifact_id, manifest_sha256_digest 
FROM submission_packages WHERE case_id = 'CASE-...';

SELECT document_id, document_type, template_name, sha256_digest
FROM document_artifacts WHERE package_id = 'PKG-...';

SELECT artifact_id, artifact_class, checksum, storage_uri
FROM evidence_artifacts WHERE linked_case_id = 'CASE-...';

SELECT current_package_id FROM permit_cases WHERE case_id = 'CASE-...';
```

**Failure visibility:**
- IntegrityError on FK violation → logged with exc_type in activity.error
- Missing case → RuntimeError with case_id
- Race condition → idempotent return with idempotent=1 log

## Deviations

**Minor deviation**: Task plan verification command was `-k persistence`, but test is named `test_persist_submission_package`, so verification required `-k persist` instead. Intent was clear and test matches task requirements.

**Implementation detail**: Added Pydantic config fix to `DocumentArtifactPayload` — removed separate `Config` class and merged `arbitrary_types_allowed=True` into `model_config = ConfigDict(...)` to avoid Pydantic 2.x validation error.

## Known Issues

None. The persistence activity currently uses placeholder digests (`"placeholder_digest_for_t02"`) because document generation hasn't been implemented yet. T03 will wire real digest computation from the evidence registry when generating documents from templates.

## Files Created/Modified

- `src/sps/db/models.py` — Added SubmissionPackage and DocumentArtifact ORM models with foreign keys to evidence_artifacts
- `alembic/versions/a1b2c3d4e5f6_submission_packages.py` — Migration creating submission_packages and document_artifacts tables
- `src/sps/documents/registry.py` — EvidenceRegistry helper for sha256-validated artifact storage
- `src/sps/workflows/permit_case/contracts.py` — Added PersistSubmissionPackageRequest activity contract
- `src/sps/workflows/permit_case/activities.py` — persist_submission_package activity with transactional package persistence
- `src/sps/documents/contracts.py` — Fixed Pydantic config issue (merged Config class into model_config)
- `tests/m006_s01_document_package_test.py` — Implemented test_persist_submission_package with full verification
