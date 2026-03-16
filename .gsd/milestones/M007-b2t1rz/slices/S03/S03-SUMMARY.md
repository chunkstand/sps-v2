---
id: S03
parent: M007-b2t1rz
milestone: M007-b2t1rz
provides:
  - Live submission + tracking runbook with receipt evidence + external status persistence assertions
requires:
  - slice: S01
    provides: SubmissionAttempt/manual fallback persistence + receipt evidence linkage
  - slice: S02
    provides: ExternalStatusEvent normalization + ingest API
affects:
  - M007-b2t1rz milestone closeout
key_files:
  - scripts/verify_m007_s03.sh
  - scripts/lib/assert_postgres.sh
  - src/sps/workflows/permit_case/workflow.py
key_decisions:
  - none
patterns_established:
  - Runbook fixture cleanup clears deterministic fixture IDs before each live run
observability_surfaces:
  - scripts/verify_m007_s03.sh output (runbook.pass / runbook.fail lines + Postgres summaries)
  - .gsd/runbook/m007_s03_api_*.log
  - .gsd/runbook/m007_s03_worker_*.log
drill_down_paths:
  - .gsd/milestones/M007-b2t1rz/slices/S03/tasks/T01-SUMMARY.md
duration: 2.5h
verification_result: passed
completed_at: 2026-03-16
---

# S03: Live submission + tracking runbook

**Operational runbook proves live submission + tracking with receipt evidence and external status persistence.**

## What Happened
Built a Phase 7 runbook (`scripts/verify_m007_s03.sh`) that boots the docker-compose stack, applies migrations, starts the real API + worker with a unique Temporal task queue, and drives intake → review decision → workflow submission. The runbook fetches submission attempts, validates receipt evidence metadata + download URLs, ingests an external status event, and asserts Postgres persistence through the existing assertion helpers. A workflow normalization fix ensures submission adapter results are consistently validated in the workflow sandbox to keep the runbook execution deterministic.

## Verification
- `bash scripts/verify_m007_s03.sh`
- `rg "runbook.fail" scripts/verify_m007_s03.sh`

## Requirements Advanced
- R016 — Operational runbook proves live submission + receipt evidence persistence using real API/worker entrypoints.
- R017 — Operational runbook proves external status ingest + persistence via live API.
- R019 — Operational runbook proves reviewer confirmation + proof bundle gate is exercised before SUBMITTED.

## Requirements Validated
- None — S03 adds operational proof but does not change validation status already proven in S01/S02 tests.

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- Updated PermitCaseWorkflow adapter result normalization to handle activity results that already implement `model_dump` (required for runbook execution).

## Known Limitations
- Runbook covers the fully supported portal submission path; manual fallback remains covered by S01 integration tests only.

## Follow-ups
- Consider adding a manual fallback runbook path when operational proof for unsupported portals is needed.

## Files Created/Modified
- `scripts/verify_m007_s03.sh` — end-to-end docker-compose runbook for intake → submission → status ingest with evidence + Postgres assertions.
- `scripts/lib/assert_postgres.sh` — leveraged for runbook assertions (no functional change in this slice).
- `src/sps/workflows/permit_case/workflow.py` — normalize submission adapter result payloads before validation.

## Forward Intelligence
### What the next slice should know
- The runbook relies on fixture override env vars for Phase 4–7 datasets and cleans fixture IDs before each run; keep that cleanup pattern for future operational runbooks.

### What's fragile
- Temporal task queue selection is unique per runbook; using the same queue across concurrent runs can lead to non-deterministic workflow starts.

### Authoritative diagnostics
- `scripts/verify_m007_s03.sh` PASS/FAIL lines + `.gsd/runbook/m007_s03_*.log` tails are the fastest signal when the live stack fails.

### What assumptions changed
- Submission adapter activity results are not always raw dicts; they may already provide `model_dump`, so workflow normalization must handle both.
