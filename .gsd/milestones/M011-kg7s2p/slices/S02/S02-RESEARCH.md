# S02 — Research

**Date:** 2026-03-16

## Summary

S01 delivered all the post-submission artifact persistence infrastructure (models, migrations, activities, API endpoints) and workflow state branches, but **status event ingestion does not yet trigger workflow continuations or call the new persistence activities**. The workflow has branches for SUBMITTED → COMMENT_REVIEW_PENDING, CORRECTION_PENDING → RESUBMISSION_PENDING, etc., but these states are never entered because there's no mechanism to signal the workflow when an ExternalStatusEvent arrives. The integration tests written in S01 (m011_s01_status_event_artifacts_test.py, m011_s01_resubmission_workflow_test.py) are structurally correct but deferred because they require a running Temporal server + full Postgres setup.

The fastest path forward is to: (1) add a new workflow signal handler (StatusEventSignal) that branches on normalized_status and calls the appropriate persist_* activity, (2) add an API endpoint (POST /api/v1/cases/{case_id}/status-events) that normalizes the raw status via persist_external_status_event and then signals the workflow (mirroring the ReviewDecision pattern in reviews.py), (3) provision a local Temporal + Postgres environment via docker-compose up, and (4) write an end-to-end runbook script that exercises submit → comment → resubmit → approve → inspect lifecycle with curl + Postgres assertions.

Primary recommendation: follow the existing ReviewDecision signal pattern. Add a StatusEventSignal contract with normalized_status + event_id fields; add a @workflow.signal handler that matches on normalized_status and dispatches to persist_correction_task / persist_resubmission_package / persist_approval_record / persist_inspection_milestone activities; create a POST /status-events API endpoint that calls persist_external_status_event then sends the StatusEventSignal to the workflow (asyncio.wait_for with 10s timeout, same as _send_review_signal); prove it works with the deferred S01 integration tests (now executable against the provisioned environment) before writing the docker-compose runbook.

## Recommendation

Follow the established signal-based workflow continuation pattern from M003/S01 (ReviewDecision). Add a new `StatusEventSignal` workflow signal with fields `event_id` and `normalized_status`. Extend PermitCaseWorkflow with a `@workflow.signal(name="StatusEvent")` handler that branches on `normalized_status` and calls the appropriate persistence activity (persist_correction_task for COMMENT_ISSUED, persist_resubmission_package for RESUBMISSION_REQUESTED, etc.). Create a new API endpoint `POST /api/v1/cases/{case_id}/status-events` (protected with intake role RBAC) that: (1) calls `persist_external_status_event` to normalize and store the event, (2) constructs a `StatusEventSignal` payload, (3) sends the signal to the workflow via `handle.signal("StatusEvent", ...)` with `asyncio.wait_for(timeout=10)`. This mirrors the exact pattern in `src/sps/api/routes/reviews.py::create_review_decision` and keeps the Postgres write as the durable record while making signal failures recoverable (logged but not HTTP-blocking).

For the runbook: use docker-compose.yml (already configured with postgres + temporal + temporal-ui + minio services) to provision the local environment. Write a bash script (scripts/verify_m011_s02.sh) that: (1) starts docker-compose services, (2) runs alembic migrations via docker exec, (3) starts the SPS worker in the background (pointing at docker Temporal + Postgres), (4) starts the API server (uvicorn) in the background, (5) exercises the full lifecycle via curl (create case → submit → POST status-event with COMMENT_ISSUED → POST status-event with RESUBMISSION_REQUESTED → POST status-event with APPROVAL_FINAL → POST status-event with INSPECTION_PASSED), (6) uses docker exec postgres psql assertions to verify correction_tasks / resubmission_packages / approval_records / inspection_milestones rows exist, and (7) tears down the stack. This proves the end-to-end integration without requiring manual operator intervention.

Once the docker-compose environment is provisioned and the StatusEvent API + signal handler exist, the deferred S01 integration tests (tests/m011_s01_status_event_artifacts_test.py, tests/m011_s01_resubmission_workflow_test.py) should pass when executed with `SPS_RUN_TEMPORAL_INTEGRATION=1` against the running Temporal server.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Workflow signal delivery + timeout handling | `_send_review_signal` in `src/sps/api/routes/reviews.py` | Already proven pattern: asyncio.wait_for(handle.signal(...), timeout=10) with logged failures that don't affect HTTP response; signal failure is recoverable and doesn't corrupt Postgres state. |
| External status normalization + fail-closed mapping | `persist_external_status_event` in `src/sps/workflows/permit_case/activities.py` | Provides fail-closed status handling (ValueError on unknown raw_status), fixture-driven mapping selection, and idempotent persistence with case/submission_attempt validation. |
| Idempotent artifact persistence pattern | `persist_correction_task` / `persist_resubmission_package` / etc. in S01 | Already implements PK check + IntegrityError race handling + re-query fallback; proven structurally correct in S01. |
| Docker-compose local dev stack | `docker-compose.yml` (postgres + temporal + minio) | Already configured with all required services; just needs `docker compose up -d` to provision. |
| Runbook pattern + Postgres assertions | `scripts/verify_m010_s03.sh` (ops read-only runbook) | Demonstrates curl + docker exec postgres psql pattern for end-to-end verification without requiring host psql or DSN handling. |

## Existing Code and Patterns

- `src/sps/api/routes/reviews.py::create_review_decision` — async endpoint that persists ReviewDecision to Postgres then sends ReviewDecisionSignal to workflow via `_send_review_signal`; signal delivery is logged but doesn't block HTTP 201 response; this is the exact pattern to follow for status events.
- `src/sps/api/routes/reviews.py::_send_review_signal` — helper function that gets workflow handle via `client.get_workflow_handle(workflow_id=f"permit-case/{case_id}")` and sends signal with `await asyncio.wait_for(handle.signal("ReviewDecision", ...), timeout=10.0)`; logs signal failures without raising.
- `src/sps/workflows/permit_case/workflow.py::review_decision` — `@workflow.signal(name="ReviewDecision")` handler that stores signal payload in workflow state and unblocks `workflow.wait_condition` in the main run method; shows the signal→state→condition pattern.
- `src/sps/workflows/permit_case/activities.py::persist_external_status_event` — activity that calls `select_status_mapping_for_case`, validates raw_status against fixture mappings, normalizes to `ExternalStatusClass`, and persists to `external_status_events` table with idempotent PK check.
- `src/sps/workflows/permit_case/activities.py::persist_correction_task` / `persist_resubmission_package` / `persist_approval_record` / `persist_inspection_milestone` — S01-delivered idempotent persistence activities with case_id + submission_attempt_id validation; follow existing activity log pattern (activity.start / activity.ok / activity.error).
- `src/sps/workflows/permit_case/workflow.py` (lines 893-914, 916-992, 994-1014, 1016-1108) — S01-delivered workflow branches for SUBMITTED (waiting state), COMMENT_REVIEW_PENDING → CORRECTION_PENDING, CORRECTION_PENDING (waiting state), RESUBMISSION_PENDING → DOCUMENT_COMPLETE (loop back to regenerate package); these branches exist but are never entered without status event signals.
- `docker-compose.yml` — configured with postgres (port 5432), temporal (port 7233), temporal-ui (port 8080), minio (ports 9000/9001); includes init scripts for database/role creation; ready to use with `docker compose up -d`.
- `docker/postgres/init/00-init.sql` — creates `sps`, `temporal`, `temporal_visibility` databases and roles; idempotent.
- `scripts/verify_m010_s03.sh` — example runbook showing curl + service-principal JWT + docker exec postgres psql assertions; provides template for M011/S02 runbook.
- `tests/m011_s01_resubmission_workflow_test.py` — deferred Temporal integration test that creates a case, transitions it through SUBMITTED → COMMENT_REVIEW_PENDING → CORRECTION_PENDING → RESUBMISSION_PENDING → DOCUMENT_COMPLETE → SUBMITTED (second attempt) workflow path; structurally correct and will pass once Temporal server is running.
- `tests/m011_s01_status_event_artifacts_test.py` — deferred integration test that calls persist_correction_task / persist_resubmission_package / persist_approval_record / persist_inspection_milestone activities directly and validates artifact creation + idempotent replay; structurally correct and will pass once database setup is complete (blocked on SubmissionPackage FK dependencies).
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — S01-extended fixture with 9 post-submission status mappings (COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_PENDING_INSPECTION, APPROVAL_FINAL, INSPECTION_SCHEDULED, INSPECTION_PASSED, INSPECTION_FAILED, APPROVAL_REPORTED, REJECTION_REPORTED); these are the normalized statuses the workflow signal handler will branch on.

## Constraints

- **Workflow determinism:** StatusEventSignal handler must not perform any I/O directly; all persistence must remain in activities called via `workflow.execute_activity`.
- **Signal delivery is best-effort:** Mirroring ReviewDecision pattern, signal delivery failures must be logged but must not affect HTTP response status; Postgres write is the durable record, signal is the trigger.
- **Status normalization is fail-closed:** Unknown raw_status values cause `persist_external_status_event` to raise ValueError; this must propagate to the API endpoint and return 400 to the caller.
- **Case/submission_attempt validation:** All persistence activities validate that submission_attempt_id belongs to case_id before insert; bypassing this check will create orphaned artifacts.
- **Fixture-driven status mapping:** Status normalization depends on fixtures in `specs/sps/build-approved/fixtures/phase7/status-maps.json`; adding new statuses requires fixture updates, not code changes.
- **Docker-compose postgres port binding:** Local Postgres binds to host port 5432; if host already has postgres running on 5432, docker-compose up will fail with port conflict.
- **Temporal server readiness:** Worker and API must wait for Temporal server to be ready (port 7233 accepting connections) before starting; runbook must include readiness check or retry loop.

## Common Pitfalls

- **Missing workflow signal handler** — if StatusEventSignal is defined as a contract but not wired into PermitCaseWorkflow with `@workflow.signal`, sending the signal will silently fail (no exception, no workflow unblock). Verify signal registration with temporal CLI or workflow introspection.
- **Signal sent before workflow started** — if POST /status-events is called before the workflow is created (e.g., case exists in DB but workflow was never started), `client.get_workflow_handle` will succeed but signal delivery will fail with WorkflowNotFound. The API should either start the workflow or return 409 Conflict.
- **Idempotency key mismatch on resubmission** — if the same CorrectionTask or ResubmissionPackage is sent twice (e.g., duplicate webhook), the PK conflict must be caught and treated as idempotent success. Do not raise 500 on IntegrityError.
- **Incomplete fixture coverage** — if a real portal emits a status like "Plan Check Complete" that isn't in status-maps.json, persist_external_status_event will raise ValueError and the API will return 400. This is correct fail-closed behavior, but the error message should be clear ("UNKNOWN_RAW_STATUS").
- **Docker-compose volume persistence** — if docker-compose down is run without `-v`, postgres data and temporal history persist across runs. Runbook cleanup should use `docker compose down -v` to ensure fresh state.
- **Missing database migration before runbook** — if alembic migrations aren't run before starting the worker, activities will fail with missing table errors. Runbook must run `alembic upgrade head` (or docker exec postgres equivalent) before starting the worker.

## Open Risks

- **StatusEventSignal contract shape** — decision needed on whether to include full ExternalStatusEvent fields (raw_status, confidence, evidence_ids, etc.) or just normalized_status + event_id. Recommendation: keep it minimal (normalized_status + event_id) and let the activity re-query the full event from Postgres if needed.
- **Workflow state explosion on many status events** — if every status event is stored in workflow state (like ReviewDecision), workflows with 50+ status events will have large state payloads. Recommendation: do NOT store StatusEventSignal in workflow state; only use it as a trigger to call activities, then discard.
- **Runbook flakiness on Temporal readiness** — docker-compose up returns before Temporal server is fully ready; worker start might fail with "connection refused" if started too soon. Mitigation: add a retry loop or explicit readiness check (curl http://localhost:7233/healthz or similar).
- **SubmissionPackage FK dependency blocking artifact tests** — tests/m011_s01_status_event_artifacts_test.py requires valid SubmissionPackage rows (package_id, manifest_artifact_id) which require EvidenceArtifact rows, which require S3/MinIO setup. Recommendation: seed minimal fixture data (stub EvidenceArtifact + SubmissionPackage rows) in the test setup to unblock execution.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (not installed) |
| docker-compose | manutej/luxor-claude-marketplace@docker-compose-orchestration | available (not installed) |

## Sources

- Workflow signal pattern and delivery timeout handling (source: src/sps/api/routes/reviews.py::create_review_decision + _send_review_signal)
- Status event normalization and fail-closed mapping (source: src/sps/workflows/permit_case/activities.py::persist_external_status_event)
- Idempotent artifact persistence pattern (source: src/sps/workflows/permit_case/activities.py::persist_correction_task et al.)
- Workflow state branches for post-submission states (source: src/sps/workflows/permit_case/workflow.py lines 893-1108)
- Docker-compose stack configuration (source: docker-compose.yml + docker/postgres/init/00-init.sql)
- Runbook pattern and Postgres assertion via docker exec (source: scripts/verify_m010_s03.sh)
- Extended status map fixtures (source: specs/sps/build-approved/fixtures/phase7/status-maps.json)
- Deferred integration test structure (source: tests/m011_s01_resubmission_workflow_test.py + tests/m011_s01_status_event_artifacts_test.py)
- Decision 96 (resubmission loop state shape): track only latest submission_attempt_id in workflow state (source: .gsd/DECISIONS.md row 96)
