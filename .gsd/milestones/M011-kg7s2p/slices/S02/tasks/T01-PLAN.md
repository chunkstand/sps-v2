---
estimated_steps: 6
estimated_files: 4
---

# T01: Add StatusEventSignal workflow handler + POST /status-events API endpoint

**Slice:** S02 — Status event workflow wiring + live docker-compose runbook
**Milestone:** M011-kg7s2p

## Description

Wire normalized status events to workflow continuations by adding a StatusEventSignal contract, a workflow signal handler that branches on normalized_status and calls the appropriate persistence activity, and a POST /status-events API endpoint that persists the event then signals the workflow. Follows the established ReviewDecision signal pattern (persist to Postgres first, then send signal with asyncio.wait_for timeout, log failures without affecting HTTP response).

## Steps

1. Add StatusEventSignal contract to src/sps/workflows/permit_case/contracts.py with fields: event_id (str), normalized_status (ExternalStatusClass)
2. Add @workflow.signal(name="StatusEvent") handler in PermitCaseWorkflow (src/sps/workflows/permit_case/workflow.py) that stores the signal in workflow state (self._status_event_signal = signal) and branches on normalized_status: COMMENT_ISSUED → workflow.execute_activity(persist_correction_task, ...), RESUBMISSION_REQUESTED → persist_resubmission_package, APPROVAL_* → persist_approval_record, INSPECTION_* → persist_inspection_milestone
3. Add _send_status_event_signal helper function to src/sps/api/routes/cases.py (mirrors _send_review_signal): takes temporal_client + case_id + StatusEventSignal payload, gets workflow handle via client.get_workflow_handle(workflow_id=f"permit-case/{case_id}"), sends signal with await asyncio.wait_for(handle.signal("StatusEvent", signal), timeout=10.0), logs success (reviewer_api.signal_sent) or failure (reviewer_api.signal_failed) without raising
4. Add POST /api/v1/cases/{case_id}/status-events endpoint to src/sps/api/routes/cases.py (protected with Depends(require_roles(Role.INTAKE))): accept PersistExternalStatusEventRequest body, call persist_external_status_event activity to normalize + persist, construct StatusEventSignal(event_id=result.event_id, normalized_status=result.normalized_status), call _send_status_event_signal, return 201 with ExternalStatusEventResponse
5. Write tests/m011_s02_status_event_signal_test.py integration test: seed a PermitCase + SubmissionAttempt, start PermitCaseWorkflow, POST /status-events with COMMENT_ISSUED payload, verify external_status_events row exists, verify workflow received signal and called persist_correction_task activity, verify correction_tasks row exists with correct case_id + submission_attempt_id linkage; repeat for RESUBMISSION_REQUESTED → persist_resubmission_package, APPROVAL_FINAL → persist_approval_record, INSPECTION_PASSED → persist_inspection_milestone
6. Run pytest tests/m011_s02_status_event_signal_test.py -v to verify signal delivery + artifact persistence end-to-end

## Must-Haves

- [ ] StatusEventSignal contract with event_id + normalized_status fields
- [ ] @workflow.signal(name="StatusEvent") handler in PermitCaseWorkflow that branches on normalized_status and calls appropriate persistence activity
- [ ] _send_status_event_signal helper function following ReviewDecision pattern (asyncio.wait_for with 10s timeout, logged failures)
- [ ] POST /api/v1/cases/{case_id}/status-events endpoint (intake role protected) that persists event then signals workflow
- [ ] Integration test proving API call → Postgres row → signal delivery → activity execution → artifact persistence for all 4 artifact types

## Verification

- `pytest tests/m011_s02_status_event_signal_test.py -v` passes with 4 test cases (comment, resubmission, approval, inspection)
- POST /status-events returns 201 with event_id + normalized_status in response body
- external_status_events table has new row with raw_status + normalized_status + case_id + submission_attempt_id
- Workflow receives StatusEvent signal and calls persist_correction_task / persist_resubmission_package / persist_approval_record / persist_inspection_milestone based on normalized_status
- Artifact tables (correction_tasks / resubmission_packages / approval_records / inspection_milestones) have new rows with correct case_id + submission_attempt_id linkage

## Observability Impact

- Signals added/changed: reviewer_api.signal_sent (level=INFO, fields: workflow_id, case_id, signal_type=StatusEvent, event_id), reviewer_api.signal_failed (level=WARNING, fields: workflow_id, case_id, signal_type=StatusEvent, event_id, error), activity logs for persist_* activities (activity.start / activity.ok / activity.error with case_id + submission_attempt_id + artifact_id)
- How a future agent inspects this: grep logs for "reviewer_api.signal_sent.*StatusEvent" to verify signal delivery; query external_status_events table for raw_status + normalized_status; query artifact tables for case_id linkage; check Temporal UI (localhost:8080) for workflow signal history and activity execution
- Failure state exposed: signal delivery timeout logs include workflow_id + case_id + event_id; activity failures include case_id + submission_attempt_id + normalized_status; API 400 responses for unknown raw_status include UNKNOWN_RAW_STATUS error code + raw_status value

## Inputs

- `src/sps/api/routes/reviews.py::_send_review_signal` — established pattern for async signal delivery with timeout and logged failures
- `src/sps/workflows/permit_case/activities.py::persist_external_status_event` — normalizes raw_status and persists ExternalStatusEvent row
- `src/sps/workflows/permit_case/activities.py::persist_correction_task` (and persist_resubmission_package, persist_approval_record, persist_inspection_milestone) — S01-delivered idempotent persistence activities
- `src/sps/workflows/permit_case/workflow.py::review_decision` signal handler — pattern for @workflow.signal and storing signal in workflow state
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — extended status mappings for COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_*, INSPECTION_* statuses

## Expected Output

- `src/sps/workflows/permit_case/contracts.py` — StatusEventSignal contract added with event_id + normalized_status fields
- `src/sps/workflows/permit_case/workflow.py` — @workflow.signal(name="StatusEvent") handler added with normalized_status branching logic and activity dispatch
- `src/sps/api/routes/cases.py` — _send_status_event_signal helper function + POST /api/v1/cases/{case_id}/status-events endpoint added
- `tests/m011_s02_status_event_signal_test.py` — integration test covering all 4 artifact types (comment, resubmission, approval, inspection) with signal delivery + Postgres verification
