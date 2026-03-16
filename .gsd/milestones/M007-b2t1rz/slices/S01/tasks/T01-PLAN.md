---
estimated_steps: 4
estimated_files: 3
---

# T01: Add submission attempt + manual fallback persistence schema

**Slice:** S01 — Deterministic submission attempt + receipt + manual fallback
**Milestone:** M007-b2t1rz

## Description
Add authoritative Postgres tables for submission attempts and manual fallback packages, including evidence artifact linkage, idempotency fields, and failure metadata. This establishes the persistence boundary the workflow and adapter will rely on.

## Steps
1. Extend `src/sps/db/models.py` with `SubmissionAttempt` and `ManualFallbackPackage` models (including status enums/strings, idempotency keys, receipt artifact FK, portal metadata, and failure fields).
2. Add indexes/unique constraints required for idempotency and deterministic lookup (e.g., request_id/attempt_id, case_id).
3. Create an Alembic migration adding the new tables and constraints.
4. Update schema expectations in `tests/s01_db_schema_test.py` if needed.

## Must-Haves
- [ ] SubmissionAttempt table persists receipt EvidenceArtifact linkage and idempotency fields.
- [ ] ManualFallbackPackage table persists fallback metadata and evidence linkage.

## Verification
- `pytest tests/s01_db_schema_test.py -k submission -v -s`
- `alembic upgrade head`

## Observability Impact
- New inspection surfaces: `submission_attempts` and `manual_fallback_packages` tables expose `status`, `attempt_number`, `receipt_artifact_id`, and `last_error` for post-submit diagnostics.
- How to inspect: query latest attempt/fallback via `psql "$DATABASE_URL" -c "select status,attempt_number,receipt_artifact_id,last_error from submission_attempts order by updated_at desc limit 1"`.
- Failure visibility: errors persist in `submission_attempts.last_error` and `updated_at` for troubleshooting without inspecting logs.

## Inputs
- `src/sps/db/models.py` — existing schema patterns for evidence and workflow entities.

## Expected Output
- `src/sps/db/models.py` — new SubmissionAttempt + ManualFallbackPackage models and metadata.
- `alembic/versions/<new>_submission_attempts_manual_fallback.py` — migration creating tables and constraints.
