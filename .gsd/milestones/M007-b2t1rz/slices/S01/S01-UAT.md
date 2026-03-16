# S01: Deterministic submission attempt + receipt + manual fallback — UAT

**Milestone:** M007-b2t1rz
**Written:** 2026-03-16

## UAT Type
- UAT mode: artifact-driven
- Why this mode is sufficient: The slice is validated through integration tests exercising Postgres + MinIO persistence and workflow guards without UI surfaces.

## Preconditions
- Postgres and MinIO are running with the SPS schema migrated (`alembic upgrade head`).
- `.venv` is activated and dependencies installed.
- Environment variables for fixture overrides are optional but supported: `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE`, `SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`.

## Smoke Test
- Run `pytest tests/m007_s01_submission_attempts_test.py -v -s` and confirm it passes.

## Test Cases
### 1. Receipt-backed submission attempt (supported portal)
1. Run `pytest tests/m007_s01_submission_attempts_test.py::test_submission_attempts_integration_flow -v -s`.
2. **Expected:** SubmissionAttempt persists with `status=SUBMITTED`, `receipt_artifact_id` populated, and EvidenceArtifact row exists for the receipt.

### 2. Manual fallback package (unsupported portal)
1. Run `pytest tests/m007_s01_manual_fallback_test.py::test_manual_fallback_package_integration_flow -v -s`.
2. **Expected:** SubmissionAttempt persists with `status=MANUAL_FALLBACK` and ManualFallbackPackage persists with `proof_bundle_state=PENDING_REVIEW` and required attachments populated.

### 3. Proof bundle gate enforcement
1. Run `pytest tests/m007_s01_proof_bundle_gate_test.py::test_proof_bundle_gate_integration_flow -v -s`.
2. **Expected:** First transition to SUBMITTED is denied with `event_type=PROOF_BUNDLE_REQUIRED_DENIED`; after proof bundle confirmation, transition applies and case state becomes `SUBMITTED`.

## Edge Cases
### Idempotent submission adapter retry
1. Re-run `pytest tests/m007_s01_manual_fallback_test.py::test_manual_fallback_package_integration_flow -v -s`.
2. **Expected:** Same `submission_attempt_id` and `manual_fallback_package_id` are returned; no duplicate rows are created.

## Failure Signals
- SubmissionAttempt rows missing `receipt_artifact_id` or `manual_fallback_package_id` after test runs.
- ManualFallbackPackage `proof_bundle_state` not updated to `CONFIRMED` in proof bundle gate test.
- Integration tests failing with duplicate key errors (indicates cleanup/idempotency regression).

## Requirements Proved By This UAT
- R016 — Idempotent submission attempts and receipt persistence.
- R018 — Manual fallback package generation and persistence.
- R019 — Proof bundle validation gate before submission completion.

## Not Proven By This UAT
- R017 — Status normalization and tracking events (S02).
- Docker-compose runbook proving real API + worker entrypoints (S03).

## Notes for Tester
- Tests clean deterministic IDs before inserts; if you seed additional data manually, ensure IDs do not collide with fixed test IDs.
