# S03: Rollback Rehearsal and Post-Release Validation — UAT

**Milestone:** M009-ct4p0u
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice proves a live API path (rollback rehearsal evidence) plus a runbook template check that only makes sense against a running service and real Postgres.

## Preconditions
- Docker compose Postgres is running (`docker compose up -d postgres`).
- Migrations are applied (`.venv/bin/alembic upgrade head`).
- FastAPI server is running at `http://localhost:8000` (e.g., `.venv/bin/python -m uvicorn sps.api.main:app --host 0.0.0.0 --port 8000`).
- Reviewer API key available (default `SPS_REVIEWER_API_KEY=dev-reviewer-key`).
- `runbooks/sps/post-release-validation.md` exists in the repo.

## Smoke Test
Run `bash scripts/verify_m009_s03.sh` and confirm it exits 0 with `runbook.pass: evidence_artifact_ok`.

## Test Cases
### 1. Rollback rehearsal evidence round-trip
1. Run `bash scripts/verify_m009_s03.sh`.
2. Capture the `artifact_id` in the script output.
3. **Expected:** Script prints `runbook.pass: evidence_artifact_ok` and the evidence API returns 200 with the same `artifact_id`.

### 2. Post-release validation runbook template presence
1. Open `runbooks/sps/post-release-validation.md`.
2. Confirm stage-gated sections exist (Canary → staged rollout) and include required report fields.
3. **Expected:** The runbook includes staged validation steps and required evidence/report fields.

## Edge Cases
### Checksum mismatch rejected
1. POST `/api/v1/releases/rollbacks/rehearsals` with an intentionally wrong checksum for the payload.
2. **Expected:** API returns 422 with `detail.error=checksum_mismatch` and no evidence artifact is stored.

## Failure Signals
- `runbook.fail:*` logs in `scripts/verify_m009_s03.sh` output.
- HTTP 4xx/5xx from `/api/v1/releases/rollbacks/rehearsals` or `/api/v1/evidence/artifacts/{artifact_id}`.
- Missing or empty `artifact_id` in the rehearsal response.
- Runbook template missing or lacking stage-gated sections.

## Requirements Proved By This UAT
- R025 — rollback rehearsal evidence persistence and retrieval via evidence API.
- R026 — post-release validation template presence and stage-gated validation steps.

## Not Proven By This UAT
- Auth/RBAC enforcement for release surfaces (M010).
- Automated staged rollout tooling beyond the template/runbook.

## Notes for Tester
- The verification script assumes the API is already running; start the server before executing the runbook.
