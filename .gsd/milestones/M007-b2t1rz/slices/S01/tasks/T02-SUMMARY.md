---
id: T02
parent: S01
milestone: M007-b2t1rz
provides:
  - deterministic submission adapter activity with receipt/manual fallback persistence
  - workflow submission step + proof bundle gate transition wiring
key_files:
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/fixtures/phase7.py
  - specs/sps/build-approved/fixtures/phase7/submission_adapter.json
key_decisions:
  - None
patterns_established:
  - Idempotent activity insert + IntegrityError race reload for submission attempts
observability_surfaces:
  - submission_attempt.start|ok|error logs; submission_attempts.last_error
duration: 2h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Implement deterministic submission adapter + workflow wiring

**Added a deterministic submission adapter activity with receipt/manual fallback persistence and wired workflow transitions through proof bundle gating.**

## What Happened
- Added submission adapter contracts + deterministic ID helpers, plus Phase 7 fixture loader and fixture data for adapter inputs.
- Implemented deterministic_submission_adapter activity: idempotent SubmissionAttempt insert, receipt EvidenceArtifact persistence, manual fallback package generation, and failure metadata logging.
- Extended apply_state_transition to handle DOCUMENT_COMPLETE → MANUAL_SUBMISSION_REQUIRED/SUBMITTED with proof bundle guard.
- Wired PermitCaseWorkflow submission step after DOCUMENT_COMPLETE and registered the new activity in the worker.
- Implemented integration tests for submission attempts, manual fallback packages, and proof bundle gating.

## Verification
- `. .venv/bin/activate && alembic upgrade head`
- `. .venv/bin/activate && pytest tests/m007_s01_submission_attempts_test.py tests/m007_s01_manual_fallback_test.py tests/m007_s01_proof_bundle_gate_test.py -v -s`

## Diagnostics
- Inspect logs for `submission_attempt.start|ok|error` with correlation_id and artifact IDs.
- DB inspection: `submission_attempts`, `manual_fallback_packages`, `evidence_artifacts`, `case_transition_ledger`.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/workflows/permit_case/contracts.py` — submission adapter contracts + deterministic ID helpers.
- `src/sps/workflows/permit_case/activities.py` — deterministic submission adapter activity + proof bundle transition guard.
- `src/sps/workflows/permit_case/workflow.py` — submission step wiring + adapter invocation.
- `src/sps/workflows/worker.py` — activity registration.
- `src/sps/fixtures/phase7.py` — phase 7 fixture loader.
- `specs/sps/build-approved/fixtures/phase7/submission_adapter.json` — deterministic adapter fixtures.
- `tests/m007_s01_submission_attempts_test.py` — submission attempt integration test.
- `tests/m007_s01_manual_fallback_test.py` — manual fallback integration test.
- `tests/m007_s01_proof_bundle_gate_test.py` — proof bundle gating integration test.
- `.gsd/milestones/M007-b2t1rz/slices/S01/S01-PLAN.md` — marked T02 complete.
