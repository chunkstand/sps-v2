---
id: M007-b2t1rz
provides:
  - Deterministic submission attempts with receipt evidence + manual fallback packages wired through PermitCaseWorkflow
  - Fixture-driven external status normalization with fail-closed ExternalStatusEvent persistence
  - Live docker-compose runbook proving submission + tracking persistence via real API + worker entrypoints
key_decisions:
  - none
patterns_established:
  - Runbook fixture cleanup clears deterministic fixture IDs before each live run
  - Submission adapter activity uses idempotent insert + IntegrityError recovery for retry safety
observability_surfaces:
  - scripts/verify_m007_s03.sh runbook.pass/runbook.fail output + .gsd/runbook/m007_s03_*.log tails
  - submission_attempts.last_error + external_status_events table
  - external_status_event.persist.ok|error logs with mapping_version + raw_status
requirement_outcomes:
  - id: R016
    from_status: active
    to_status: validated
    proof: pytest tests/m007_s01_submission_attempts_test.py -v -s (idempotent receipt persistence)
  - id: R017
    from_status: active
    to_status: validated
    proof: pytest tests/m007_s02_external_status_events_test.py -v -s (known status persistence + unknown status fail-closed)
  - id: R018
    from_status: active
    to_status: validated
    proof: pytest tests/m007_s01_manual_fallback_test.py -v -s (manual fallback package persistence)
  - id: R019
    from_status: active
    to_status: validated
    proof: pytest tests/m007_s01_proof_bundle_gate_test.py -v -s (proof bundle confirmation gate)
duration: 7.7h
verification_result: passed
completed_at: 2026-03-16
---

# M007-b2t1rz: Phase 7 — submission, tracking, and manual fallback

**Submission attempts, status tracking, and manual fallback are wired end-to-end with receipt evidence, fail-closed normalization, and live runbook proof.**

## What Happened

Phase 7 delivered deterministic submission attempts with receipt evidence or manual fallback packages, wired into PermitCaseWorkflow with proof bundle confirmation gating. Status normalization was added via fixture maps with fail-closed behavior and persisted ExternalStatusEvent records, exposed through ingest/list APIs. The milestone closed with a docker-compose runbook that booted the real API and worker, executed intake → review → submission, captured receipt evidence metadata, ingested a normalized status event, and asserted Postgres persistence across the submission and tracking surfaces.

## Cross-Slice Verification

- SubmissionAttempt + receipt evidence persistence and SUBMITTED/MANUAL_SUBMISSION_REQUIRED outcomes proved via `pytest tests/m007_s01_submission_attempts_test.py -v -s`, `pytest tests/m007_s01_manual_fallback_test.py -v -s`, and operationally via `bash scripts/verify_m007_s03.sh`.
- External status normalization + fail-closed unknown status handling proved via `pytest tests/m007_s02_external_status_events_test.py -v -s` and runbook ingest + Postgres assertions in `scripts/verify_m007_s03.sh`.
- Proof bundle confirmation gate enforced before submission completion proved via `pytest tests/m007_s01_proof_bundle_gate_test.py -v -s` and the Phase 7 runbook path (review → submission).
- Live docker-compose proof of submission + tracking persistence across Postgres/Temporal/MinIO provided by `scripts/verify_m007_s03.sh` with runbook PASS lines and Postgres assertions.

## Requirement Changes

- R016: active → validated — `pytest tests/m007_s01_submission_attempts_test.py -v -s`
- R017: active → validated — `pytest tests/m007_s02_external_status_events_test.py -v -s`
- R018: active → validated — `pytest tests/m007_s01_manual_fallback_test.py -v -s`
- R019: active → validated — `pytest tests/m007_s01_proof_bundle_gate_test.py -v -s`

## Forward Intelligence

### What the next milestone should know
- The runbook relies on fixture override env vars for Phase 4–7 datasets and clears deterministic fixture IDs before each run to keep submissions idempotent.

### What's fragile
- Phase 7 fixture overrides (`SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`) are required for deterministic adapter behavior — missing overrides can shift fixture selection and break repeatability.

### Authoritative diagnostics
- `scripts/verify_m007_s03.sh` PASS/FAIL lines + `.gsd/runbook/m007_s03_*.log` tails — fastest signal for live submission/ingest failures.

### What assumptions changed
- Submission adapter activity results may already implement `model_dump`, so workflow normalization must accept both raw dicts and Pydantic-compatible payloads.

## Files Created/Modified

- `src/sps/db/models.py` — SubmissionAttempt/ManualFallbackPackage/ExternalStatusEvent models.
- `alembic/versions/c7f9e2a1b4d6_submission_attempts_manual_fallback.py` — submission/manual fallback migration.
- `alembic/versions/f0b4c9d7e2a1_external_status_events.py` — external status events migration.
- `src/sps/workflows/permit_case/activities.py` — submission adapter + status normalization activities.
- `src/sps/workflows/permit_case/workflow.py` — submission/tracking wiring + adapter result normalization.
- `src/sps/api/routes/cases.py` — submission attempt/manual fallback/status ingest endpoints.
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — status normalization fixtures.
- `scripts/verify_m007_s03.sh` — docker-compose runbook proving live submission + tracking persistence.
