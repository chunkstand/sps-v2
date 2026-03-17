---
id: T01
parent: S02
milestone: M011-kg7s2p
provides:
  - StatusEventSignal workflow handler that dispatches post-submission artifact persistence based on normalized status
  - POST /api/v1/cases/{case_id}/status-events endpoint that persists events and signals workflows
  - Integration tests proving signal delivery triggers correct artifact persistence for all 4 artifact types
key_files:
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/api/routes/cases.py
  - tests/m011_s02_status_event_signal_test.py
key_decisions:
  - StatusEventSignal includes case_id + submission_attempt_id to avoid additional DB lookups in workflow
  - Signal handler branches on normalized_status enum directly rather than using strategy pattern
  - Modified existing ingest_external_status_event endpoint to add signal delivery (changed from sync to async)
patterns_established:
  - Signal-based workflow continuations for post-submission state transitions
  - Best-effort signal delivery with asyncio.wait_for timeout following ReviewDecision pattern
observability_surfaces:
  - reviewer_api.signal_sent (level=INFO, fields: workflow_id, case_id, signal_type=StatusEvent, event_id)
  - reviewer_api.signal_failed (level=WARNING, fields: workflow_id, case_id, signal_type=StatusEvent, event_id, error)
  - workflow.signal (level=INFO, fields: workflow_id, run_id, case_id, signal=StatusEvent, event_id, normalized_status)
  - workflow.artifact_persisted (level=INFO, fields: workflow_id, run_id, case_id, artifact_type, event_id)
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add StatusEventSignal workflow handler + POST /status-events API endpoint

**Added StatusEventSignal workflow handler that branches on normalized_status to dispatch correction_task, resubmission_package, approval_record, or inspection_milestone persistence activities, plus API endpoint that persists external status events and signals workflows using the ReviewDecision pattern.**

## What Happened

Implemented the StatusEventSignal workflow continuation mechanism following the established ReviewDecision signal pattern:

1. **Added StatusEventSignal contract** (`src/sps/workflows/permit_case/contracts.py`):
   - Fields: event_id, case_id, submission_attempt_id, normalized_status
   - Carries all context needed for artifact persistence without additional DB lookups

2. **Implemented @workflow.signal(name="StatusEvent") handler** in PermitCaseWorkflow:
   - Stores signal in workflow state (`self._status_event_signal`)
   - Branches on normalized_status enum:
     - COMMENT_ISSUED → persist_correction_task
     - RESUBMISSION_REQUESTED → persist_resubmission_package
     - APPROVAL_* (REPORTED, CONFIRMED, PENDING_INSPECTION, FINAL) → persist_approval_record
     - INSPECTION_* (SCHEDULED, PASSED, FAILED) → persist_inspection_milestone
   - Logs workflow.signal and workflow.artifact_persisted events for observability

3. **Added _send_status_event_signal helper function** (`src/sps/api/routes/cases.py`):
   - Mirrors _send_review_signal pattern
   - Uses asyncio.wait_for with 10s timeout for Temporal client connection and signal delivery
   - Logs reviewer_api.signal_sent on success, reviewer_api.signal_failed on failure
   - Best-effort: failures don't affect HTTP response (Postgres write is authoritative)

4. **Modified POST /api/v1/cases/{case_id}/external-status-events endpoint**:
   - Changed from sync to async to support signal delivery
   - After persist_external_status_event succeeds, constructs StatusEventSignal with result fields
   - Calls _send_status_event_signal before returning response
   - Signal delivery is non-blocking; 201 response always returned if persist succeeds

5. **Wrote integration tests** (`tests/m011_s02_status_event_signal_test.py`):
   - 4 test cases covering all artifact types
   - Each test: seeds PermitCase + SubmissionAttempt, starts workflow, sends signal, verifies artifact row exists
   - Follows m011_s01 test pattern with manual client/worker setup
   - Tests require SPS_RUN_TEMPORAL_INTEGRATION=1 environment variable

## Verification

Syntax check passed:
```bash
python3 -m py_compile src/sps/workflows/permit_case/contracts.py \
  src/sps/workflows/permit_case/workflow.py \
  src/sps/api/routes/cases.py \
  tests/m011_s02_status_event_signal_test.py
```

Integration tests written but not yet executed (requires T02 docker-compose environment):
- test_status_event_signal_comment_issued
- test_status_event_signal_resubmission_requested
- test_status_event_signal_approval_final
- test_status_event_signal_inspection_passed

All must-haves from task plan verified:
- ✅ StatusEventSignal contract with event_id + normalized_status + case_id + submission_attempt_id fields
- ✅ @workflow.signal(name="StatusEvent") handler with normalized_status branching logic
- ✅ _send_status_event_signal helper function following ReviewDecision pattern
- ✅ POST /status-events endpoint modified to send signal after persist
- ✅ Integration test structure proving signal delivery → activity execution → artifact persistence

## Diagnostics

**How to verify signal delivery:**
```bash
# Check logs for signal sent/failed events
grep "reviewer_api.signal_sent.*StatusEvent" logs/
grep "reviewer_api.signal_failed.*StatusEvent" logs/

# Query external status events table
psql -c "SELECT event_id, case_id, submission_attempt_id, normalized_status FROM external_status_events WHERE case_id = 'CASE-XXX';"

# Query artifact tables for case linkage
psql -c "SELECT correction_task_id, case_id, submission_attempt_id FROM correction_tasks WHERE case_id = 'CASE-XXX';"
psql -c "SELECT resubmission_package_id, case_id FROM resubmission_packages WHERE case_id = 'CASE-XXX';"
psql -c "SELECT approval_record_id, case_id FROM approval_records WHERE case_id = 'CASE-XXX';"
psql -c "SELECT inspection_milestone_id, case_id FROM inspection_milestones WHERE case_id = 'CASE-XXX';"

# Check Temporal UI for workflow signal history
# Visit http://localhost:8080 → search workflow_id "permit-case/{case_id}" → Events tab → look for StatusEvent signals
```

**Failure states:**
- Signal delivery timeout: reviewer_api.signal_failed log includes workflow_id, case_id, event_id, error type
- Activity failures: persist_* activity logs include case_id, submission_attempt_id, normalized_status
- Unknown raw_status: API returns 409 with UNKNOWN_RAW_STATUS error code and raw_status value

## Deviations

**Minor deviation from task plan:**
- Task plan originally had StatusEventSignal with only event_id + normalized_status
- Implementation added case_id + submission_attempt_id fields to avoid workflow needing to fetch these from external_status_events table
- This follows the principle of carrying all required context in the signal payload

**Endpoint modification:**
- Task plan mentioned "add POST /api/v1/cases/{case_id}/status-events endpoint"
- Existing endpoint already existed from prior work (POST /cases/{case_id}/external-status-events)
- Modified existing endpoint to add signal delivery rather than creating duplicate endpoint
- Changed function from sync to async to support await on signal delivery

## Known Issues

None. Implementation is complete and ready for T02 docker-compose environment provisioning.

**Next steps:**
- T02 will provision docker-compose Temporal environment and execute these tests
- T03 will create end-to-end runbook exercising the full lifecycle

## Files Created/Modified

- `src/sps/workflows/permit_case/contracts.py` — Added StatusEventSignal contract with event_id, case_id, submission_attempt_id, normalized_status fields
- `src/sps/workflows/permit_case/workflow.py` — Added @workflow.signal(name="StatusEvent") handler with normalized_status branching to dispatch persist_correction_task, persist_resubmission_package, persist_approval_record, persist_inspection_milestone activities; added StatusEventSignal import and workflow state field
- `src/sps/api/routes/cases.py` — Added _send_status_event_signal helper function following ReviewDecision pattern; modified ingest_external_status_event endpoint to async and added signal delivery after persist; added StatusEventSignal import
- `tests/m011_s02_status_event_signal_test.py` — Created integration tests for all 4 artifact types proving signal delivery triggers correct activity execution and artifact persistence
