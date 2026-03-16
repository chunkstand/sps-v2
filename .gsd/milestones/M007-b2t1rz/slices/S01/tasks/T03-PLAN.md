---
estimated_steps: 4
estimated_files: 5
---

# T03: Expose submission attempt + receipt + fallback via API and add integration tests

**Slice:** S01 — Deterministic submission attempt + receipt + manual fallback
**Milestone:** M007-b2t1rz

## Description
Expose submission attempts, receipt evidence metadata, and manual fallback packages through the case API and add integration tests that validate idempotency, manual fallback behavior, and proof bundle gating.

## Steps
1. Add API response contracts for submission attempts, receipt evidence metadata, and manual fallback packages in `src/sps/api/contracts/cases.py`.
2. Implement GET routes in `src/sps/api/routes/cases.py` for submission attempts and manual fallback inspection.
3. Create integration tests covering:
   - Idempotent submission attempt + receipt persistence.
   - Manual fallback package generation for unsupported portals.
   - Proof bundle confirmation gate preventing SUBMITTED without confirmation.
4. Ensure tests exercise Temporal + Postgres/MinIO wiring via existing integration harness.

## Must-Haves
- [ ] API surfaces expose persisted submission attempts, receipts, and fallback packages.
- [ ] Integration tests prove idempotent submission, manual fallback, and proof bundle gating.

## Verification
- `pytest tests/m007_s01_submission_attempts_test.py -v -s`
- `pytest tests/m007_s01_manual_fallback_test.py -v -s`
- `pytest tests/m007_s01_proof_bundle_gate_test.py -v -s`

## Inputs
- `src/sps/workflows/permit_case/workflow.py` — submission wiring from T02.
- `src/sps/db/models.py` — submission attempt and manual fallback persistence.

## Expected Output
- `src/sps/api/routes/cases.py` — GET routes for submission attempts and manual fallback packages.
- `tests/m007_s01_submission_attempts_test.py` — integration tests for idempotency + receipts.
- `tests/m007_s01_manual_fallback_test.py` — integration test for manual fallback package creation.
- `tests/m007_s01_proof_bundle_gate_test.py` — integration test for proof bundle confirmation enforcement.

## Observability Impact
- New case API surfaces for submission attempts, receipt evidence metadata, and manual fallback packages; inspect via GET endpoints or DB tables to confirm state.
- Failure visibility improves through API fields exposing `status`, `attempt_number`, `receipt_artifact_id`, `manual_fallback_package_id`, and `last_error` values already persisted in `submission_attempts` and `manual_fallback_packages`.
- Integration tests exercise Temporal/Postgres/MinIO wiring so failures surface as test assertion failures plus DB rows for inspection.
