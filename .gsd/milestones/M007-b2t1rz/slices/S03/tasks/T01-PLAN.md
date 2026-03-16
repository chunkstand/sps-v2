---
estimated_steps: 6
estimated_files: 3
---
# T01: Build Phase 7 runbook for live submission + tracking

**Slice:** S03 — Live submission + tracking runbook
**Milestone:** M007-b2t1rz

## Description
Create a Phase 7 runbook script that boots the docker-compose stack, runs migrations, starts API + worker against a dedicated Temporal task queue, drives intake through reviewer approval and submission, ingests an external status event, and asserts receipt + status persistence via API + Postgres without leaking DSNs.

## Steps
1. Copy the lifecycle scaffolding from `scripts/verify_m005_s03.sh` (compose up/down, migration, API/worker boot, cleanup traps) into `scripts/verify_m007_s03.sh`.
2. Add Phase 6 + Phase 7 fixture overrides and deterministic fixture cleanup (delete by fixture IDs) before starting the run.
3. Drive intake, post a reviewer decision using the reviewer API key, and wait for submission outcomes (SUBMITTED or MANUAL_SUBMISSION_REQUIRED).
4. Fetch submission attempts + receipt evidence metadata, request the evidence download URL, and ingest a known raw external status tied to the submission attempt.
5. Assert Postgres rows for submission attempts, evidence artifacts, and external status events using `scripts/lib/assert_postgres.sh`.
6. Ensure logging avoids secrets and exits non-zero on any failed assertion.

## Must-Haves
- [ ] Runbook sets unique `SPS_TEMPORAL_TASK_QUEUE` and Phase 6/7 fixture override env vars before starting API/worker.
- [ ] Runbook drives intake → reviewer decision → submission attempt and records receipt evidence metadata + download URL.
- [ ] Runbook ingests a known raw status and asserts `external_status_events` persistence.
- [ ] All Postgres checks use `docker compose exec` via `scripts/lib/assert_postgres.sh`.

## Verification
- `bash scripts/verify_m007_s03.sh`
- Runbook exits 0 and prints receipt evidence + status event assertions.

## Observability Impact
- Signals added/changed: runbook output includes API response summaries and explicit PASS/FAIL lines for receipt + status checks.
- How a future agent inspects this: rerun `scripts/verify_m007_s03.sh` and review assertion output; spot-check API endpoints for submission attempts and external status events.
- Failure state exposed: non-zero exit plus specific assertion failure output (missing receipt artifact, missing status event, workflow never submitted).

## Inputs
- `scripts/verify_m005_s03.sh` — lifecycle scaffolding and docker-compose orchestration pattern.
- `scripts/lib/assert_postgres.sh` — Postgres assertion helper (no DSN leakage).
- `src/sps/api/routes/cases.py` — submission attempt + external status endpoints used by runbook.

## Expected Output
- `scripts/verify_m007_s03.sh` — operational runbook proving live submission + tracking persistence.
