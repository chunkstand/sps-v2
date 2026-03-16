---
estimated_steps: 6
estimated_files: 5
---

# T02: Persist submission packages and evidence artifacts
**Slice:** S01 — Deterministic document artifacts + submission package persistence
**Milestone:** M006-h7v2qk

## Description
Introduce the database schema and persistence activity for SubmissionPackage + DocumentArtifact, plus an internal evidence registry helper that writes document/manifest content to S3 with sha256 validation. This establishes the storage boundary needed for deterministic package sealing.

## Steps
1. Add SQLAlchemy models for `SubmissionPackage` and `DocumentArtifact` (plus any linking fields) and create an Alembic migration.
2. Implement `src/sps/documents/registry.py` to register evidence artifacts, upload content via `S3Storage`, and return artifact IDs + digests from final bytes.
3. Add workflow activity contract(s) for package persistence in `src/sps/workflows/permit_case/contracts.py`.
4. Implement a persistence activity in `src/sps/workflows/permit_case/activities.py` that stores package rows, artifact rows, and updates `permit_cases.current_package_id` in a single transaction.
5. Update tests to assert direct package persistence behavior (DB rows + evidence metadata) without workflow wiring.
6. Run the persistence-focused test subset.

## Must-Haves
- [ ] SubmissionPackage + DocumentArtifact schema/migration lands with deterministic IDs and evidence linkage.
- [ ] Evidence registry helper stores content with sha256 checks and returns manifest/document artifact IDs + digests.

## Verification
- `pytest tests/m006_s01_document_package_test.py -k persistence -v`

## Observability Impact
- Signals added/changed: activity logs for package persistence start/ok/error with package_id + case_id.
- How a future agent inspects this: Postgres tables `submission_packages`, `document_artifacts`, `evidence_artifacts` plus evidence metadata endpoints.
- Failure state exposed: checksum mismatch or S3 upload failure logged with artifact_id and checksum.

## Inputs
- `src/sps/evidence/ids.py` — stable artifact ID + object key conventions.
- `src/sps/storage/s3.py` — storage adapter used by evidence uploads.

## Expected Output
- `src/sps/db/models.py` + `alembic/versions/*_submission_packages.py` — SubmissionPackage/DocumentArtifact schema.
- `src/sps/documents/registry.py` — evidence registration helper with sha256 enforcement.
- `src/sps/workflows/permit_case/activities.py` — persistence activity for packages.
