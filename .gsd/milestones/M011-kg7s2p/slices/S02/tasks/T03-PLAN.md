---
estimated_steps: 8
estimated_files: 2
---

# T03: Write end-to-end docker-compose runbook for post-submission lifecycle

**Slice:** S02 — Status event workflow wiring + live docker-compose runbook
**Milestone:** M011-kg7s2p

## Description

Write an automated bash runbook (scripts/verify_m011_s02.sh) that provisions the docker-compose stack, starts the SPS worker and API server, exercises the full post-submission lifecycle (create case → submit → POST 4 status events for comment/resubmission/approval/inspection), verifies artifact creation via Postgres assertions, and cleans up all resources. Proves the end-to-end integration of API + worker + Postgres + Temporal with observable evidence.

## Steps

1. Write scripts/verify_m011_s02.sh header: set -euo pipefail, source scripts/start_temporal_dev.sh to provision docker-compose services
2. Start SPS worker in background: export SPS_TEMPORAL_ADDRESS=localhost:7233 SPS_DB_DSN=postgresql://sps:sps@localhost:5432/sps, run python -m sps.worker &, save PID for cleanup
3. Start API server in background: export same env vars, run uvicorn sps.api.main:app --host 0.0.0.0 --port 8000 &, save PID for cleanup
4. Wait for API readiness: retry loop (curl -f http://localhost:8000/healthz || sleep 1, max 30 attempts), exit 1 on timeout
5. Exercise lifecycle: (1) build intake JWT with roles=["intake"], (2) POST /api/v1/cases with fixture intake payload (use CASE-EXAMPLE-001 fixture shape), save case_id, (3) POST /api/v1/cases/{case_id}/submit (triggers workflow to SUBMITTED state), (4) POST /api/v1/cases/{case_id}/status-events with COMMENT_ISSUED fixture payload (normalized_status + raw_status + confidence), (5) POST /status-events with RESUBMISSION_REQUESTED payload, (6) POST /status-events with APPROVAL_FINAL payload, (7) POST /status-events with INSPECTION_PASSED payload
6. Verify artifacts via docker exec postgres psql: (1) assert correction_tasks row exists for case_id, (2) assert resubmission_packages row exists, (3) assert approval_records row exists, (4) assert inspection_milestones row exists; each assertion: docker compose exec postgres psql -U sps -d sps -c "SELECT task_id FROM correction_tasks WHERE case_id='${case_id}'" | grep -q CORR- || (echo "FAIL: no correction task" && exit 1)
7. Cleanup: kill worker PID, kill API PID, docker compose down -v (removes volumes for fresh state on next run)
8. Exit 0 on success (all assertions passed), exit 1 on any failure (API call failed, assertion failed, timeout)

## Must-Haves

- [ ] scripts/verify_m011_s02.sh provisions docker-compose stack via scripts/start_temporal_dev.sh
- [ ] Worker and API server start in background with correct env vars (SPS_TEMPORAL_ADDRESS, SPS_DB_DSN)
- [ ] API readiness check (curl /healthz retry loop) before exercising lifecycle
- [ ] Full lifecycle exercised: create case → submit → POST 4 status events (COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_FINAL, INSPECTION_PASSED)
- [ ] Postgres assertions verify all 4 artifact types exist (correction_tasks, resubmission_packages, approval_records, inspection_milestones) with correct case_id linkage
- [ ] Cleanup kills worker + API processes and runs docker compose down -v for fresh state
- [ ] Runbook exits 0 on success, 1 on any failure

## Verification

- `bash scripts/verify_m011_s02.sh` exits 0 after completing all lifecycle steps and assertions
- docker compose ps shows services stopped after cleanup (down -v removes containers)
- docker volume ls shows no sps-related volumes after cleanup
- Manual inspection: comment "# Verify artifact creation" before cleanup, run psql manually to confirm rows exist: docker compose exec postgres psql -U sps -d sps -c "SELECT * FROM correction_tasks;" shows 1 row with case_id matching the created case

## Observability Impact

- Signals added/changed: runbook stdout logs each lifecycle step (STEP: creating case, STEP: submitting case, STEP: posting COMMENT_ISSUED event, etc.); assertion output logs (PASS: correction task found, FAIL: no resubmission package); worker logs include activity execution (persist_correction_task, etc.); API logs include request handling (POST /status-events)
- How a future agent inspects this: run bash scripts/verify_m011_s02.sh and read stdout for PASS/FAIL messages; docker compose logs worker to see activity execution; docker compose logs api to see endpoint handling; docker compose exec postgres psql to manually query artifact tables
- Failure state exposed: runbook exits 1 with error message (FAIL: no correction task, FAIL: API readiness timeout, FAIL: POST /status-events returned 400, etc.); worker logs include activity failures with case_id + submission_attempt_id; API logs include 400/500 responses with error details

## Inputs

- `scripts/start_temporal_dev.sh` — provisions docker-compose services (from T02)
- `src/sps/worker.py` — worker entrypoint for Temporal activity execution
- `src/sps/api/main.py` — FastAPI app entrypoint for uvicorn
- `src/sps/api/routes/cases.py` — POST /cases, POST /submit, POST /status-events endpoints (from T01)
- `src/sps/workflows/permit_case/workflow.py` — PermitCaseWorkflow with StatusEventSignal handler (from T01)
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — status mapping fixtures for COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_FINAL, INSPECTION_PASSED
- `scripts/verify_m010_s03.sh` — reference runbook showing curl + JWT + docker exec postgres psql pattern

## Expected Output

- `scripts/verify_m011_s02.sh` — automated end-to-end runbook proving submit → comment → resubmit → approve → inspect lifecycle with Postgres evidence
- `scripts/stop_temporal_dev.sh` (optional) — manual cleanup helper (docker compose down -v) for operator use outside runbook
- Runbook execution output showing PASS for all assertions (correction_tasks, resubmission_packages, approval_records, inspection_milestones rows exist)
- Clean docker-compose state after runbook completes (no containers, no volumes)
