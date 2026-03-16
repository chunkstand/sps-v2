---
id: S01
parent: M007-b2t1rz
milestone: M007-b2t1rz
provides:
  - SubmissionAttempt + ManualFallbackPackage persistence with receipt EvidenceArtifact linkage
  - Deterministic submission adapter activity with idempotent receipt/manual fallback handling
  - Proof bundle confirmation gate enforced before SUBMITTED transition
  - Case API read surfaces for submission attempts and manual fallback packages
requires:
  - none (first slice in M007)
affects:
  - M007/S02
key_files:
  - src/sps/db/models.py
  - alembic/versions/c7f9e2a1b4d6_submission_attempts_manual_fallback.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/worker.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m007_s01_submission_attempts_test.py
  - tests/m007_s01_manual_fallback_test.py
  - tests/m007_s01_proof_bundle_gate_test.py
key_decisions:
  - none
patterns_established:
  - Submission adapter activity uses idempotent insert + IntegrityError recovery for retry safety
  - Manual fallback packages derive deterministic IDs from submission attempt IDs
observability_surfaces:
  - submission_attempt.start|ok|error logs with attempt_id, receipt_artifact_id, manual_fallback_id
  - DB tables: submission_attempts, manual_fallback_packages, evidence_artifacts, case_transition_ledger
  - API endpoints: GET /cases/{case_id}/submission-attempts, GET /cases/{case_id}/manual-fallbacks
  - submission_attempts.last_error for failure visibility
  - diagnostic query via SQLAlchemy (submission_attempts status + last_error)
drill_down_paths:
  - .gsd/milestones/M007-b2t1rz/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007-b2t1rz/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M007-b2t1rz/slices/S01/tasks/T03-SUMMARY.md
duration: 3.7h
verification_result: passed
completed_at: 2026-03-16T17:30:00Z
---

# S01: Deterministic submission attempt + receipt + manual fallback

**Deterministic submission attempts persist receipts or manual fallback packages with proof bundle gating and API read surfaces.**

## What Happened
Built the submission attempt and manual fallback persistence path end-to-end. The slice introduced SubmissionAttempt and ManualFallbackPackage schema, a deterministic submission adapter activity that handles retry-safe persistence with receipt evidence registration or manual fallback creation, and workflow wiring to enforce proof bundle confirmation before SUBMITTED. API read endpoints expose submission attempts and manual fallback packages with embedded evidence metadata, and integration tests now cover the success path, unsupported portal fallback, and proof bundle gating. Tests were updated to clean prior test rows to keep reruns deterministic.

## Verification
- `pytest tests/m007_s01_submission_attempts_test.py tests/m007_s01_manual_fallback_test.py tests/m007_s01_proof_bundle_gate_test.py -v -s`
- Observability check (SQLAlchemy): queried latest submission_attempts status + last_error

## Requirements Advanced
- R016 — Idempotent submission attempts and receipt persistence wired through workflow + API surfaces.
- R018 — Manual fallback packages are generated and persisted for unsupported portal workflows.
- R019 — Proof bundle confirmation gate enforced before SUBMITTED transition.

## Requirements Validated
- R016 — Proven by `tests/m007_s01_submission_attempts_test.py` (idempotent receipt persistence).
- R018 — Proven by `tests/m007_s01_manual_fallback_test.py` (manual fallback persistence).
- R019 — Proven by `tests/m007_s01_proof_bundle_gate_test.py` (proof bundle gate).

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- Status normalization + tracking events (R017) not yet implemented (S02).
- Docker-compose runbook proof is deferred to S03.

## Follow-ups
- Implement status normalization + ExternalStatusEvent persistence in S02.

## Files Created/Modified
- `src/sps/db/models.py` — submission attempt + manual fallback models
- `alembic/versions/c7f9e2a1b4d6_submission_attempts_manual_fallback.py` — schema migration
- `src/sps/workflows/permit_case/contracts.py` — submission adapter contracts + deterministic ID helpers
- `src/sps/workflows/permit_case/activities.py` — deterministic submission adapter + proof bundle guard
- `src/sps/workflows/permit_case/workflow.py` — submission step wiring
- `src/sps/workflows/worker.py` — activity registration
- `src/sps/api/contracts/cases.py` — submission attempt/manual fallback API models
- `src/sps/api/routes/cases.py` — submission attempt/manual fallback endpoints
- `tests/m007_s01_submission_attempts_test.py` — submission attempt integration test
- `tests/m007_s01_manual_fallback_test.py` — manual fallback integration test (with cleanup)
- `tests/m007_s01_proof_bundle_gate_test.py` — proof bundle gate integration test (with cleanup)

## Forward Intelligence
### What the next slice should know
- The submission adapter relies on Phase 7 fixture overrides (`SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`) and will fail closed when no fixture is available.

### What's fragile
- Manual fallback tests assume stable IDs; cleanup is required if the integration DB persists between runs.

### Authoritative diagnostics
- `submission_attempts.last_error` and `submission_attempts.status` are the fastest signals for retry failures and fallbacks.

### What assumptions changed
- Tests now need explicit cleanup for deterministic IDs in persistent integration databases.
