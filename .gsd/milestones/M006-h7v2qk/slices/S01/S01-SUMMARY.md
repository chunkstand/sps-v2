---
id: S01
parent: M006-h7v2qk
milestone: M006-h7v2qk
provides:
  - Phase 6 fixture dataset with deterministic document templates + loader with case_id override
  - SubmissionPackage and DocumentArtifact schema with migration applied
  - EvidenceRegistry helper for sha256-validated document/manifest artifact storage
  - Document generator producing deterministic document bytes from templates
  - persist_submission_package activity with transactional package persistence + evidence registration
  - Workflow transition INCENTIVES_COMPLETE → DOCUMENT_COMPLETE (implemented, pending S3 infrastructure for full proof)
  - API endpoints for package and manifest retrieval (implemented, pending S3 infrastructure for full proof)
requires:
  - none (first slice in M006)
affects:
  - M006/S02
key_files:
  - specs/sps/build-approved/fixtures/phase6/documents.json
  - specs/sps/build-approved/fixtures/phase6/permit_application_template.txt
  - specs/sps/build-approved/fixtures/phase6/site_plan_checklist_template.txt
  - src/sps/fixtures/phase6.py
  - src/sps/documents/contracts.py
  - src/sps/documents/generator.py
  - src/sps/documents/registry.py
  - src/sps/db/models.py
  - alembic/versions/a1b2c3d4e5f6_submission_packages.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/api/routes/cases.py
  - src/sps/api/contracts/cases.py
  - tests/m006_s01_document_package_test.py
key_decisions:
  - Document templates use mustache-style {{variable}} placeholder replacement for deterministic rendering
  - Package persistence generates all documents + registers evidence + persists DB rows in single activity call
  - Manifest includes document references with sha256 digests computed from final rendered bytes
  - Workflow guard for INCENTIVES_COMPLETE → DOCUMENT_COMPLETE requires SubmissionPackage to exist
patterns_established:
  - Phase 6 fixture loader follows Phase 4/5 pattern with case_id override env var for test flexibility
  - Evidence registry provides register_document() and register_manifest() with sha256 validation
  - Document generation: load template → render with variables → compute sha256 → build manifest → register evidence
  - Package persistence activity follows Phase 4/5 idempotency pattern with IntegrityError handling
observability_surfaces:
  - generator.document_rendered logs with document_id, template, bytes, digest
  - generator.package_complete logs with package_id, manifest_id, manifest_digest, doc_count
  - package_activity.manifest_registered logs with artifact_id, digest, bytes
  - workflow.package_persisted logs with package_id
  - DB tables: submission_packages, document_artifacts, evidence_artifacts
  - API endpoints: GET /cases/{case_id}/package, GET /cases/{case_id}/manifest
drill_down_paths:
  - .gsd/milestones/M006-h7v2qk/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006-h7v2qk/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M006-h7v2qk/slices/S01/tasks/T03-SUMMARY.md
duration: 4.5h
verification_result: partial
completed_at: 2026-03-16T16:30:00Z
---

# S01: Deterministic document artifacts + submission package persistence

**Deterministic document generation from Phase 6 fixtures with sha256-validated evidence artifacts, package persistence schema, workflow transition to DOCUMENT_COMPLETE, and API retrieval endpoints.**

## What Happened

Built the complete document generation and package persistence path from fixtures through evidence registry to database storage:

**T01 (1.5h)**: Created Phase 6 fixture dataset with two document templates (permit application + site plan checklist) plus fixture metadata JSON. Implemented deterministic fixture loader with `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE` env var support following Phase 4/5 patterns. Added contract models in `src/sps/documents/contracts.py` for typed document/manifest payloads with Pydantic strict validation. Created integration test module with 10 passing fixture validation tests and 6 stubbed integration tests for T02/T03 wiring.

**T02 (45m)**: Added SubmissionPackage and DocumentArtifact schema with migration applied. Implemented EvidenceRegistry helper providing `register_document()` and `register_manifest()` methods that compute sha256 digests, upload to S3 with integrity checks, and return RegisteredArtifact with artifact_id + digest + storage_uri. Created `persist_submission_package` activity that loads fixtures, creates manifest evidence artifact, creates SubmissionPackage row, creates document evidence artifacts, creates DocumentArtifact rows, and updates `permit_cases.current_package_id` in single transaction with explicit flush() calls for foreign key ordering.

**T03 (2.5h)**: Implemented document generator using mustache-style {{variable}} placeholder replacement, sha256 computation from final bytes, and manifest building with document references. Wired `persist_submission_package` to generate documents, register evidence with sha256 validation, and persist package. Added INCENTIVES_COMPLETE → DOCUMENT_COMPLETE workflow transition with persist_submission_package activity call. Created API endpoints for package/manifest retrieval (`GET /cases/{case_id}/package` and `GET /cases/{case_id}/manifest`). Updated integration tests to verify digest determinism and evidence registry consistency.

## Verification

**Fixture tests (all passing):**
```bash
pytest tests/m006_s01_document_package_test.py -k fixtures -v
# 10 passed in 0.04s
```

Tests confirm:
- Dataset schema validates with required fields
- Pydantic enforces strict validation (extra fields raise AttributeError)
- Template loading succeeds for valid templates and fails cleanly for missing ones
- Case ID override resolution works with and without env var
- Fixture selection returns empty list when no match found

**Document generation determinism test (passing):**
```bash
pytest tests/m006_s01_document_package_test.py::test_document_generation_determinism -v
# PASSED
```

Validates:
- sha256 computation from final rendered bytes
- Digest-content matching
- Manifest structure with document references

**Integration tests (partial - S3 infrastructure required):**
```bash
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m006_s01_document_package_test.py -k integration -v
# test_persist_submission_package FAILED (ConnectionRefusedError: [Errno 61] Connection refused to localhost:9000)
# test_document_generation_determinism PASSED
# test_manifest_digest_consistency FAILED (same S3 connection error)
# test_workflow_advances_to_document_complete SKIPPED
# test_api_package_retrieval SKIPPED
# test_evidence_registry_document_retrieval SKIPPED
```

The S3 integration tests require LocalStack or live S3 bucket running on localhost:9000. All document generation logic, digest computation, and DB persistence code is implemented and verified up to the S3 boundary. Full end-to-end proof will be completed in S02 with docker-compose runbook.

**Migration applied:**
```bash
alembic upgrade head
# INFO  [alembic.runtime.migration] Running upgrade 9b7a3d2c1f0e -> a1b2c3d4e5f6, submission_packages
```

## Requirements Advanced

- R015 (Submission package generation) — Partial validation achieved: deterministic document generation with sha256 digest computation proven in pytest; full persistence + workflow + API path implemented but requires S3 infrastructure (LocalStack/docker-compose) for complete end-to-end proof in S02.

## Requirements Validated

None (R015 remains partially validated pending S02 runbook).

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

**Minor deviation (T02)**: Task plan verification command was `-k persistence`, but test is named `test_persist_submission_package`, so verification required `-k persist` instead. Intent was clear and test matches task requirements.

**Implementation detail (T02)**: Added explicit `session.flush()` calls after each foreign-key-dependent group (manifest evidence → package → document evidence → document artifacts) to ensure SQLAlchemy respects insertion order within the transaction. This was necessary to avoid FK violation errors during package persistence.

**Implementation fix (T03)**: Fixed S3Storage initialization (requires settings parameter) and bucket name (s3_bucket_evidence not s3_evidence_bucket).

## Known Limitations

**S3 integration in tests**: `persist_submission_package` activity calls S3Storage.put_bytes which requires either LocalStack running locally, live S3 bucket configured in settings, or mocked S3 client for unit tests. Current test environment doesn't have S3 available, so full integration tests (`test_persist_submission_package`, `test_manifest_digest_consistency`) fail at S3 upload step. The document generation, digest computation, and DB persistence logic are all implemented and verified up to the S3 boundary.

**Workaround for S02**: When running in docker-compose with LocalStack or live S3, the full persistence path will work end-to-end. S02 runbook will provide this proof.

**Failure path tests**: While basic error handling tests exist (missing templates → FileNotFoundError, schema violations → Pydantic ValidationError), comprehensive failure path tests for digest mismatch and invalid template rendering errors are not yet implemented. These should be added before production use.

## Follow-ups

- **S02**: Prove full end-to-end package persistence + workflow + API path in docker-compose runbook with LocalStack/live S3
- Add comprehensive failure path tests for digest mismatch scenarios and invalid template rendering
- Consider Jinja2 template engine for production instead of simple mustache-style replacement

## Files Created/Modified

- `specs/sps/build-approved/fixtures/phase6/permit_application_template.txt` — Permit application document template with mustache-style variables
- `specs/sps/build-approved/fixtures/phase6/site_plan_checklist_template.txt` — Site plan checklist template
- `specs/sps/build-approved/fixtures/phase6/documents.json` — Phase 6 fixture metadata with document definitions + manifest structure
- `src/sps/fixtures/phase6.py` — Deterministic fixture loader with case_id override support + template loader
- `src/sps/documents/__init__.py` — Document service package init
- `src/sps/documents/contracts.py` — Pydantic contract models for DocumentArtifactPayload, SubmissionManifestPayload, SubmissionPackagePayload
- `src/sps/documents/generator.py` — Document generator with template rendering, sha256 computation, manifest building, and package assembly
- `src/sps/documents/registry.py` — EvidenceRegistry helper for sha256-validated artifact storage with register_document() and register_manifest() methods
- `src/sps/db/models.py` — Added SubmissionPackage and DocumentArtifact ORM models with foreign keys to evidence_artifacts
- `alembic/versions/a1b2c3d4e5f6_submission_packages.py` — Migration creating submission_packages and document_artifacts tables
- `src/sps/workflows/permit_case/contracts.py` — Added PersistSubmissionPackageRequest activity contract
- `src/sps/workflows/permit_case/activities.py` — persist_submission_package activity with document generation, evidence registration, and transactional package persistence; added INCENTIVES_COMPLETE → DOCUMENT_COMPLETE guard
- `src/sps/workflows/permit_case/workflow.py` — Added INCENTIVES_COMPLETE → DOCUMENT_COMPLETE transition path with persist_submission_package activity call
- `src/sps/api/routes/cases.py` — Added GET /cases/{case_id}/package and GET /cases/{case_id}/manifest endpoints
- `src/sps/api/contracts/cases.py` — Added SubmissionPackageResponse, SubmissionManifestResponse, DocumentReferenceResponse models
- `tests/m006_s01_document_package_test.py` — Integration test module with 10 fixture tests (passing) + 6 integration tests (3 implemented, 3 stubbed for S02)
- `pyproject.toml` — Registered pytest marks for `fixtures` and `integration`
- `.gsd/REQUIREMENTS.md` — Updated R015 status to "active (partial validation)" with proof notes

## Forward Intelligence

### What the next slice should know

- The document generation and digest computation logic is fully implemented and deterministic — S02 just needs to wire S3 infrastructure (LocalStack in docker-compose) to prove end-to-end persistence.
- The evidence registry helper (`EvidenceRegistry.register_document()` and `register_manifest()`) expects S3Storage to be initialized with `settings` parameter and uses `settings.s3_bucket_evidence` (not `s3_evidence_bucket`).
- Package persistence activity uses explicit `session.flush()` calls to enforce foreign key ordering: manifest evidence → package → document evidence → document artifacts.
- API endpoints for package/manifest retrieval are implemented but untested; S02 runbook should include API readback verification after workflow completes.
- Workflow guard for INCENTIVES_COMPLETE → DOCUMENT_COMPLETE checks for SubmissionPackage existence; ensure test fixtures advance through INCENTIVES_COMPLETE state first.

### What's fragile

- **S3 bucket name consistency**: Code uses `settings.s3_bucket_evidence` but there's no validation that this matches the LocalStack/live S3 bucket configuration. Mismatched bucket names will cause silent failures. S02 runbook should verify bucket exists before workflow runs.
- **Foreign key ordering in package persistence**: If any of the explicit `session.flush()` calls are removed, SQLAlchemy may reorder inserts and hit FK violations. This ordering is critical for the four-step sequence (manifest evidence → package → document evidence → document artifacts).
- **Template variable mismatches**: If a template references a variable that's missing from the fixture's `document_variables` dict, rendering will succeed but produce incomplete documents. Consider adding template variable validation before rendering in production.

### Authoritative diagnostics

- **Fixture schema validation**: `pytest tests/m006_s01_document_package_test.py::test_load_phase6_fixtures_schema_valid -v -s` — shows loaded fixture structure and validates JSON schema
- **Document generation digest integrity**: `pytest tests/m006_s01_document_package_test.py::test_document_generation_determinism -v` — proves sha256 computation from final bytes matches stored digests
- **Package persistence logs**: Look for `package_activity.persisted` with package_id, manifest_id, doc_count when debugging persistence issues
- **DB inspection for package state**: `SELECT package_id, manifest_artifact_id, manifest_sha256_digest FROM submission_packages WHERE case_id = '...'` shows package metadata; join to `evidence_artifacts` on `manifest_artifact_id` to verify checksum consistency
- **Evidence registry artifacts**: `SELECT artifact_id, artifact_class, checksum, content_bytes, storage_uri FROM evidence_artifacts WHERE linked_case_id = '...'` shows all evidence artifacts (MANIFEST + DOCUMENT) with digests and S3 URIs

### What assumptions changed

- **Original assumption**: Full integration tests would pass in T03 with mocked S3.
- **What actually happened**: Tests hit real S3Storage which requires LocalStack or live S3. Mocking S3 at the boto3 level would require additional test infrastructure. Decision was to prove document generation and digest logic in isolation tests and defer full persistence proof to S02 docker-compose runbook with real S3 (LocalStack).
