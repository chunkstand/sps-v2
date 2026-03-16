---
id: S03
parent: M009-ct4p0u
milestone: M009-ct4p0u
provides:
  - rollback rehearsal evidence endpoint + post-release validation runbook verification
requires:
  - slice: S02
    provides: release bundle manifest generation + blocker gates
affects:
  - M010/S01
key_files:
  - src/sps/api/routes/releases.py
  - src/sps/evidence/models.py
  - tests/m009_s03_rollback_rehearsal_test.py
  - scripts/verify_m009_s03.sh
  - runbooks/sps/post-release-validation.md
key_decisions:
  - Canonicalize rollback rehearsal payload JSON before checksum validation.
patterns_established:
  - EvidenceRegistry-backed release evidence endpoints with release retention.
observability_surfaces:
  - rollback_rehearsal.* structured logs
  - GET /api/v1/evidence/artifacts/{artifact_id}
  - scripts/verify_m009_s03.sh output
  - EvidenceArtifacts table


drill_down_paths:
  - .gsd/milestones/M009-ct4p0u/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009-ct4p0u/slices/S03/tasks/T02-SUMMARY.md
duration: 2.2h
verification_result: passed
completed_at: 2026-03-16
---

# S03: Rollback Rehearsal and Post-Release Validation

**Rollback rehearsal evidence endpoints and the post-release validation runbook now ship with end-to-end verification.**

## What Happened
- Added rollback rehearsal evidence persistence via the evidence registry with checksum validation and release-scoped retention.
- Shipped a stage-gated post-release validation runbook template and a verification script that posts a rehearsal artifact and retrieves it via the evidence API.
- Ran integration tests and the operational verification script against a live API to prove the endpoint, evidence lookup, and runbook template presence.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py -k failure`
- `bash scripts/verify_m009_s03.sh`

## Requirements Advanced
- none

## Requirements Validated
- R025 — rollback rehearsal evidence verified via integration tests + `scripts/verify_m009_s03.sh`.
- R026 — post-release validation template verified via runbook existence + `scripts/verify_m009_s03.sh`.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- `scripts/verify_m009_s03.sh` expects a running FastAPI service and does not boot the API itself.

## Follow-ups
- none

## Files Created/Modified
- `src/sps/evidence/models.py` — added `ROLLBACK_REHEARSAL` artifact class.
- `src/sps/api/routes/releases.py` — rollback rehearsal endpoint with evidence registry persistence.
- `tests/m009_s03_rollback_rehearsal_test.py` — integration coverage for persistence + checksum mismatch handling.
- `runbooks/sps/post-release-validation.md` — stage-gated post-release validation template.
- `scripts/verify_m009_s03.sh` — runbook verification script for rollback rehearsal evidence.

## Forward Intelligence
### What the next slice should know
- The rollback rehearsal endpoint expects canonicalized JSON payloads (sorted keys + compact separators) for checksum validation.

### What's fragile
- `scripts/verify_m009_s03.sh` requires a live API on port 8000; missing service leads to curl errors.

### Authoritative diagnostics
- `scripts/verify_m009_s03.sh` output + `GET /api/v1/evidence/artifacts/{artifact_id}` confirm evidence persistence.

### What assumptions changed
- Assumed the runbook script would be self-contained; it now depends on an externally started API server.
