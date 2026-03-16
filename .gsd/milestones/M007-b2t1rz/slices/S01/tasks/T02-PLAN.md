---
estimated_steps: 5
estimated_files: 4
---

# T02: Implement deterministic submission adapter + workflow wiring

**Slice:** S01 — Deterministic submission attempt + receipt + manual fallback
**Milestone:** M007-b2t1rz

## Description
Implement the deterministic submission adapter activity, wire it into the PermitCaseWorkflow, and enforce proof bundle confirmation before SUBMITTED. The activity must be idempotent under retries and persist receipt evidence or manual fallback packages.

## Steps
1. Add submission attempt contracts in `src/sps/workflows/permit_case/contracts.py` for request/response payloads and deterministic identifiers.
2. Implement a deterministic submission adapter activity in `src/sps/workflows/permit_case/activities.py` that:
   - Writes a SubmissionAttempt idempotently using request_id/attempt_id.
   - Persists a receipt EvidenceArtifact and links it to the attempt.
   - Generates a ManualFallbackPackage when portal support is unsupported.
   - Records failure metadata when adapter execution fails.
3. Enforce proof bundle confirmation in the workflow prior to marking SUBMITTED, and wire the activity into the submission step in `src/sps/workflows/permit_case/workflow.py`.
4. Register the new activity in `src/sps/workflows/worker.py` and add fixture definitions under `specs/sps/build-approved/fixtures/phase7/` for deterministic adapter inputs.
5. Add structured logs with correlation_id, attempt_id, receipt_artifact_id/manual_fallback_id, and status transitions.

## Must-Haves
- [ ] Submission adapter activity is idempotent under retries and persists receipt evidence.
- [ ] Workflow transitions to SUBMITTED or MANUAL_SUBMISSION_REQUIRED with proof bundle confirmation enforced.

## Verification
- `pytest tests/m007_s01_submission_attempts_test.py -v -s`

## Observability Impact
- Signals added/changed: activity logs `submission_attempt.start|ok|error` with correlation_id and artifact IDs; submission_attempts.last_error updates on failure.
- How a future agent inspects this: query `submission_attempts`/`manual_fallback_packages` tables or read workflow logs via test output.
- Failure state exposed: status + last_error + updated_at on SubmissionAttempt rows.

## Inputs
- `src/sps/db/models.py` — SubmissionAttempt + ManualFallbackPackage tables from T01.
- `specs/sps/build-approved/fixtures/phase7/` — fixture placement conventions.

## Expected Output
- `src/sps/workflows/permit_case/activities.py` — deterministic submission adapter activity with receipt/manual fallback persistence.
- `src/sps/workflows/permit_case/workflow.py` — submission step wired with proof bundle confirmation gate.
- `src/sps/workflows/worker.py` — activity registered for runtime execution.
