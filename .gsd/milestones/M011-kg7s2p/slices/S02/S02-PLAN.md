# S02: Status event workflow wiring + live docker-compose runbook

**Goal:** Wire normalized status events to workflow continuations that persist post-submission artifacts, and prove the end-to-end comment → resubmission → approval/inspection lifecycle in a live docker-compose environment with Postgres evidence.

**Demo:** Start docker-compose (postgres + temporal + worker + API), submit a case, POST status events (COMMENT_ISSUED → RESUBMISSION_REQUESTED → APPROVAL_FINAL → INSPECTION_PASSED), query Postgres to verify correction_tasks / resubmission_packages / approval_records / inspection_milestones rows exist with correct case_id and submission_attempt_id linkage. Deferred S01 integration tests pass against the provisioned environment.

## Must-Haves

- StatusEventSignal workflow signal handler that branches on normalized_status and calls persist_correction_task / persist_resubmission_package / persist_approval_record / persist_inspection_milestone activities
- POST /api/v1/cases/{case_id}/status-events API endpoint (intake role protected) that persists ExternalStatusEvent then signals the workflow with asyncio.wait_for(timeout=10) following ReviewDecision pattern
- docker-compose up provisions postgres + temporal + temporal-ui services with alembic migrations applied
- SPS worker starts against docker Temporal + Postgres and registers PermitCaseWorkflow + all activities
- End-to-end runbook script (scripts/verify_m011_s02.sh) exercises create case → submit → POST 4 status events → psql assertions on artifact tables → teardown
- Deferred S01 integration tests (tests/m011_s01_status_event_artifacts_test.py, tests/m011_s01_resubmission_workflow_test.py) pass when executed with SPS_RUN_TEMPORAL_INTEGRATION=1 against provisioned environment

## Proof Level

- This slice proves: operational (live API + worker + Postgres + Temporal integration with end-to-end runbook)
- Real runtime required: yes (docker-compose stack with postgres, temporal, worker, API)
- Human/UAT required: no (runbook is automated bash script with psql assertions)

## Verification

- `pytest tests/m011_s01_status_event_artifacts_test.py -v` (deferred S01 test, now executable against provisioned Temporal + Postgres)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s` (deferred S01 workflow test, now executable)
- `bash scripts/verify_m011_s02.sh` (end-to-end runbook proving submit → comment → resubmit → approve → inspect lifecycle with Postgres evidence)

## Observability / Diagnostics

- Runtime signals: StatusEventSignal delivery logs (reviewer_api.signal_sent / reviewer_api.signal_failed), activity logs (activity.start name=persist_correction_task / persist_resubmission_package / etc.), transition ledger rows (case_transition_ledger with guard assertions for post-submission states)
- Inspection surfaces: GET /api/v1/cases/{case_id}/correction-tasks (and /resubmission-packages, /approval-records, /inspection-milestones), docker exec postgres psql queries on artifact tables, temporal UI (http://localhost:8080) showing workflow state and activity history
- Failure visibility: signal delivery timeout logs include workflow_id + case_id correlation; activity failures include case_id + submission_attempt_id + artifact_id; API 400 responses for unknown raw_status include UNKNOWN_RAW_STATUS error code
- Redaction constraints: raw_status and evidence_ids are not PII/secret; no redaction needed for status event payloads

## Integration Closure

- Upstream surfaces consumed: persist_external_status_event (M007/S01), persist_correction_task / persist_resubmission_package / persist_approval_record / persist_inspection_milestone (M011/S01), PermitCaseWorkflow state branches (M011/S01), ReviewDecision signal pattern (M003/S01)
- New wiring introduced in this slice: StatusEventSignal handler in PermitCaseWorkflow, POST /status-events API endpoint → persist_external_status_event → signal workflow → activity dispatch, docker-compose environment provisioning with alembic migrations + worker startup
- What remains before the milestone is truly usable end-to-end: external status event ingestion (webhook/polling mechanism to feed POST /status-events endpoint); currently requires manual API calls

## Tasks

- [x] **T01: Add StatusEventSignal workflow handler + POST /status-events API endpoint** `est:1.5h`
  - Why: Wire status event normalization to workflow continuations so normalized events trigger artifact persistence activities; follows established ReviewDecision signal pattern
  - Files: `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/api/routes/cases.py`, `tests/m011_s02_status_event_signal_test.py`
  - Do: Add StatusEventSignal contract with event_id + normalized_status fields; add @workflow.signal(name="StatusEvent") handler in PermitCaseWorkflow that branches on normalized_status (COMMENT_ISSUED → persist_correction_task, RESUBMISSION_REQUESTED → persist_resubmission_package, APPROVAL_* → persist_approval_record, INSPECTION_* → persist_inspection_milestone); add POST /api/v1/cases/{case_id}/status-events endpoint (intake role protected) that calls persist_external_status_event then sends StatusEventSignal via _send_status_event_signal helper (mirrors _send_review_signal with asyncio.wait_for(timeout=10)); write integration test proving API call → Postgres row → signal delivery → activity execution
  - Verify: `pytest tests/m011_s02_status_event_signal_test.py -v`
  - Done when: POST /status-events returns 201, external_status_events row exists, workflow receives StatusEventSignal and calls appropriate persistence activity, artifact row exists in Postgres with correct case_id + submission_attempt_id linkage

- [x] **T02: Provision docker-compose Temporal environment + execute deferred S01 tests** `est:1h`
  - Why: Deferred S01 integration tests are structurally correct but blocked on Temporal server + full Postgres setup; provisioning the environment proves the tests and infrastructure are ready
  - Files: `docker-compose.yml`, `scripts/start_temporal_dev.sh`, `tests/m011_s01_status_event_artifacts_test.py`, `tests/m011_s01_resubmission_workflow_test.py`
  - Do: Verify docker-compose.yml has postgres (port 5432), temporal (port 7233), temporal-ui (port 8080) services with init scripts; write scripts/start_temporal_dev.sh that runs docker compose up -d, waits for Temporal port 7233 readiness (nc -z localhost 7233 || sleep 1 retry loop), runs alembic upgrade head via docker exec postgres, returns once services are ready; seed minimal SubmissionPackage + EvidenceArtifact fixture rows to unblock tests/m011_s01_status_event_artifacts_test.py FK dependencies; run both deferred tests with SPS_RUN_TEMPORAL_INTEGRATION=1 against the provisioned environment
  - Verify: `bash scripts/start_temporal_dev.sh && pytest tests/m011_s01_status_event_artifacts_test.py -v && SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s`
  - Done when: Both deferred S01 tests pass against live Temporal + Postgres; docker-compose services remain running for T03 runbook

- [x] **T03: Write end-to-end docker-compose runbook for post-submission lifecycle** `est:1.5h`
  - Why: Prove the full comment → resubmission → approval/inspect lifecycle with real API + worker + Postgres + Temporal; provides operator-friendly verification and documents the integration
  - Files: `scripts/verify_m011_s02.sh`, `scripts/stop_temporal_dev.sh`
  - Do: Write scripts/verify_m011_s02.sh that: (1) starts docker-compose via scripts/start_temporal_dev.sh, (2) starts SPS worker in background (python -m sps.worker with docker Temporal + Postgres DSN), (3) starts API server in background (uvicorn sps.api.main:app --port 8000), (4) waits for API readiness (curl http://localhost:8000/healthz retry loop), (5) creates a case via POST /cases with intake JWT, (6) submits the case via POST /cases/{case_id}/submit, (7) POSTs 4 status events (COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_FINAL, INSPECTION_PASSED) via POST /status-events with fixture payloads, (8) asserts correction_tasks / resubmission_packages / approval_records / inspection_milestones rows exist via docker exec postgres psql queries, (9) kills worker + API processes, (10) runs docker compose down -v for cleanup; write scripts/stop_temporal_dev.sh for manual cleanup; runbook exits 0 on success, 1 on any assertion failure
  - Verify: `bash scripts/verify_m011_s02.sh`
  - Done when: Runbook completes all lifecycle steps with exit 0; psql assertions verify all 4 artifact types exist with correct case_id linkage; cleanup leaves no docker volumes

## Files Likely Touched

- `src/sps/workflows/permit_case/contracts.py` (StatusEventSignal contract)
- `src/sps/workflows/permit_case/workflow.py` (signal handler + activity dispatch)
- `src/sps/api/routes/cases.py` (POST /status-events endpoint + _send_status_event_signal helper)
- `tests/m011_s02_status_event_signal_test.py` (integration test for T01)
- `scripts/start_temporal_dev.sh` (docker-compose startup + readiness check)
- `scripts/verify_m011_s02.sh` (end-to-end lifecycle runbook)
- `scripts/stop_temporal_dev.sh` (manual cleanup helper)
- `tests/m011_s01_status_event_artifacts_test.py` (deferred test, now executable)
- `tests/m011_s01_resubmission_workflow_test.py` (deferred test, now executable)
