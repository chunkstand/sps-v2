---
id: T02
parent: S03
milestone: M009-ct4p0u
provides:
  - post-release validation runbook template and verification script for rollback rehearsal evidence
key_files:
  - runbooks/sps/post-release-validation.md
  - scripts/verify_m009_s03.sh
key_decisions:
  - none
patterns_established:
  - runbook verification script asserts template presence + rollback rehearsal evidence retrieval
observability_surfaces:
  - scripts/verify_m009_s03.sh output (runbook.* logs, non-zero exits on API/template failures)
duration: 35m
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Add post-release validation runbook + verification script

**Added the post-release validation runbook template and a verification script that posts a rollback rehearsal artifact, retrieves evidence metadata, and fails closed when anything is missing.**

## What Happened
- Added `runbooks/sps/post-release-validation.md` with stage-gated (canary → staged rollout) validation steps, required report fields, and closure evidence.
- Implemented `scripts/verify_m009_s03.sh` to check the template exists, POST rollback rehearsal evidence, and GET the resulting artifact metadata, with explicit curl error handling.

## Verification
- `bash scripts/verify_m009_s03.sh`
  - **Failed**: `curl_error action=create_rehearsal` (API not running on localhost:8000).

## Diagnostics
- Re-run `bash scripts/verify_m009_s03.sh` with a running API; failures emit `runbook.fail:*` logs and exit non-zero.
- Evidence metadata can be inspected via `GET /api/v1/evidence/artifacts/{artifact_id}`.

## Deviations
- None.

## Known Issues
- Verification script requires a running API; current run failed due to connection refusal on localhost:8000.

## Files Created/Modified
- `runbooks/sps/post-release-validation.md` — post-release validation runbook with stage gates and report fields.
- `scripts/verify_m009_s03.sh` — verification script for rollback rehearsal evidence + template presence.
