---
id: S01
parent: M012-v8s3qn
milestone: M012-v8s3qn
provides:
  - Emergency + override artifact persistence with time bounds, scoped APIs, and guard enforcement in workflow transitions
requires: []
affects: []
key_files:
  - src/sps/db/models.py
  - alembic/versions/37a1384857bd_emergency_override_artifacts.py
  - src/sps/api/routes/emergencies.py
  - src/sps/api/routes/overrides.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - tests/m012_s01_override_guard_test.py
  - tests/m012_s01_emergency_hold_test.py
  - scripts/verify_m012_s01.sh
key_decisions:
  - Composite indexes on (case_id, expires_at) for emergency_records/override_artifacts to optimize active-artifact queries
  - cleanup_due_at = expires_at + 24h to define bounded emergency cleanup window
  - Override guard runs before contradiction guard when override_id is supplied
  - EMERGENCY_HOLD → SUBMITTED transitions are forbidden with STATE_TRANSITION_DENIED
patterns_established:
  - Override denial emits OVERRIDE_DENIED ledger entries with guard_assertion_id=INV-SPS-EMERG-001
  - Emergency/override artifact APIs follow RBAC-gated artifact creation pattern with ULID IDs
observability_surfaces:
  - workflow.override_denied (WARNING) log
  - emergency_api.emergency_declared and override_api.override_created logs
  - docker compose exec -T postgres psql -U sps -d sps -c "SELECT override_id, expires_at < NOW() as expired FROM override_artifacts ORDER BY created_at DESC LIMIT 5"
  - docker compose exec -T postgres psql -U sps -d sps -c "SELECT event_type, payload->>'guard_assertion_id' FROM case_transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY occurred_at DESC LIMIT 3"
drill_down_paths:
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T04-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T05-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T06-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T07-SUMMARY.md
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T08-SUMMARY.md
duration: 10h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Emergency/override artifacts + guard enforcement + lifecycle proof

**Emergency declaration + override artifacts are now persisted, enforced in the transition guard, and proven end-to-end with Temporal/Postgres integration tests and a docker-compose lifecycle runbook.**

## What Happened
Implemented EmergencyRecord and OverrideArtifact persistence with migrations and composite indexes, then added RBAC-gated emergency/override APIs with time-bounded enforcement. Wired override validation into the apply_state_transition guard with OVERRIDE_DENIED ledger events and added EMERGENCY_HOLD entry/exit workflow signaling with validation activities plus a forbidden EMERGENCY_HOLD → SUBMITTED transition. Added Temporal/Postgres integration tests for override guard and EMERGENCY_HOLD lifecycle, and delivered a docker-compose runbook that exercises declare → override → expire → deny → cleanup with live API/worker/Postgres assertions.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 uv run pytest tests/m012_s01_override_guard_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 uv run pytest tests/m012_s01_emergency_hold_test.py -v`
- `bash scripts/verify_m012_s01.sh`
- Observability checks:
  - `docker compose exec -T postgres psql -U sps -d sps -c "SELECT override_id, expires_at < NOW() as expired FROM override_artifacts ORDER BY created_at DESC LIMIT 5"`
  - `docker compose exec -T postgres psql -U sps -d sps -c "SELECT event_type, payload->>'guard_assertion_id' FROM case_transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY occurred_at DESC LIMIT 3"`

## Requirements Advanced
- None.

## Requirements Validated
- R034 — Integration tests + docker-compose runbook prove emergency declaration, override enforcement, and EMERGENCY_HOLD lifecycle with OVERRIDE_DENIED audit trails.

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- None.

## Known Limitations
- None.

## Follow-ups
- None.

## Files Created/Modified
- `src/sps/db/models.py` — EmergencyRecord + OverrideArtifact ORM models
- `alembic/versions/37a1384857bd_emergency_override_artifacts.py` — emergency/override tables migration
- `src/sps/api/routes/emergencies.py` — emergency declaration endpoint
- `src/sps/api/routes/overrides.py` — override creation endpoint
- `src/sps/workflows/permit_case/activities.py` — override guard + EMERGENCY_HOLD enforcement
- `src/sps/workflows/permit_case/workflow.py` — EMERGENCY_HOLD entry/exit handlers
- `tests/m012_s01_override_guard_test.py` — override guard integration tests
- `tests/m012_s01_emergency_hold_test.py` — EMERGENCY_HOLD lifecycle integration tests
- `scripts/verify_m012_s01.sh` — docker-compose lifecycle runbook

## Forward Intelligence
### What the next slice should know
- The runbook (`scripts/verify_m012_s01.sh`) provisions docker-compose and tears it down; re-run `scripts/start_temporal_dev.sh` before ad-hoc DB inspections.

### What's fragile
- Review decision signaling in the runbook may log workflow-not-found warnings when cases are seeded directly in Postgres; this is expected but can confuse log-only checks.

### Authoritative diagnostics
- `case_transition_ledger` rows for `OVERRIDE_DENIED` with `guard_assertion_id=INV-SPS-EMERG-001` are the definitive enforcement signal.

### What assumptions changed
- None.
