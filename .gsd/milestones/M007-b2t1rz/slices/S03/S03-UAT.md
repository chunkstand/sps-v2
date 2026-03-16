# S03: Live submission + tracking runbook — UAT

**Milestone:** M007-b2t1rz
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: This slice’s proof is operational; the runbook must execute against real API + worker entrypoints and persistence backends.

## Preconditions
- Docker + docker-compose available.
- `.venv` exists with project dependencies installed.
- Ports 5432 (Postgres), 7233 (Temporal), 9000 (MinIO), and 8000 (API) are available.
- Optional env overrides (if needed): `SPS_DB_*`, `SPS_TEMPORAL_*`, `SPS_REVIEWER_API_KEY`, `API_HOST`, `API_PORT`.

## Smoke Test
Run `bash scripts/verify_m007_s03.sh` and confirm it exits 0 with `runbook: ok` and `runbook.pass:` lines for receipt evidence + external status ingest.

## Test Cases
### 1. End-to-end submission + receipt evidence
1. Run `bash scripts/verify_m007_s03.sh`.
2. Observe `runbook: submission_attempt_ok` and the JSON payload printed after `fetching_submission_attempts`.
3. **Expected:** Output includes `runbook.pass: receipt_evidence_ok` and a receipt evidence download URL from `/api/v1/evidence/artifacts/{id}/download`.

### 2. External status ingest persistence
1. Run `bash scripts/verify_m007_s03.sh` (fresh run or immediately after test case 1).
2. Observe `runbook.pass: external_status_ingest_ok` and `runbook.pass: postgres_assertions_ok`.
3. **Expected:** `runbook: postgres_summary` shows an `external_status_events` row with the raw status and normalized status.

## Edge Cases
### Re-run idempotency / cleanup
1. Run `bash scripts/verify_m007_s03.sh` twice in a row.
2. **Expected:** Both runs exit 0; fixture cleanup prevents deterministic ID conflicts and both runs emit `runbook.pass:` lines.

## Failure Signals
- Any `runbook.fail:` output or non-zero exit code.
- Missing `runbook.pass: receipt_evidence_ok` or `runbook.pass: external_status_ingest_ok`.
- `runbook: postgres_summary` missing SUBMITTED transition or external status row.

## Requirements Proved By This UAT
- R016 — live submission attempt + receipt evidence persistence via real API/worker runbook.
- R017 — live external status ingest + persistence via real API/worker runbook.
- R019 — reviewer confirmation + proof bundle gate exercised before submission completes.

## Not Proven By This UAT
- Manual fallback generation (R018) — covered by S01 integration tests only.
- Unknown status fail-closed behavior — covered by S02 integration tests.

## Notes for Tester
- The runbook brings up docker-compose services and shuts them down on exit.
- API/worker logs are captured under `.gsd/runbook/` for troubleshooting on failure.
