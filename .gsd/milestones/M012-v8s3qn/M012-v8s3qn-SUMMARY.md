---
id: M012-v8s3qn
provides:
  - Emergency declaration + override artifacts with time bounds, guard enforcement, and EMERGENCY_HOLD lifecycle proof
key_decisions:
  - Override guard runs before contradiction guard when override_id is supplied
  - cleanup_due_at is computed as expires_at + 24 hours for bounded emergency cleanup
patterns_established:
  - OVERRIDE_DENIED ledger entries include guard_assertion_id=INV-SPS-EMERG-001
  - Emergency/override APIs follow RBAC-gated artifact creation with ULID identifiers
observability_surfaces:
  - workflow.override_denied (WARNING) log
  - emergency_api.emergency_declared and override_api.override_created logs
  - docker compose exec -T postgres psql -U sps -d sps -c "SELECT override_id, expires_at < NOW() as expired FROM override_artifacts ORDER BY created_at DESC LIMIT 5"
  - docker compose exec -T postgres psql -U sps -d sps -c "SELECT event_type, payload->>'guard_assertion_id' FROM case_transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY occurred_at DESC LIMIT 3"
requirement_outcomes:
  - id: R034
    from_status: active
    to_status: validated
    proof: pytest tests/m012_s01_override_guard_test.py -v + pytest tests/m012_s01_emergency_hold_test.py -v + scripts/verify_m012_s01.sh runbook
duration: 10h
verification_result: passed
completed_at: 2026-03-16
---

# M012-v8s3qn: Phase 12 — emergency and override governance

**Emergency and override workflows are now explicit, time-bounded, enforced in the transition guard, and proven end-to-end with integration tests and a docker-compose lifecycle runbook.**

## What Happened

Built EmergencyRecord and OverrideArtifact persistence with time-bound validation and RBAC-gated APIs, then wired override validation into `apply_state_transition` with OVERRIDE_DENIED ledger denials and EMERGENCY_HOLD entry/exit enforcement in the workflow. Added Temporal/Postgres integration tests for override guard behavior and EMERGENCY_HOLD lifecycle, and delivered a docker-compose runbook that exercises declare → override → protected transition → expire → deny → cleanup with live API/worker/Postgres verification.

## Cross-Slice Verification

- Emergency declaration and override artifact creation are proven via `tests/m012_s01_override_guard_test.py` and the docker-compose lifecycle runbook (`scripts/verify_m012_s01.sh`), which asserts persisted artifacts and guard denials.
- Override enforcement semantics (allow valid override, deny missing/expired override) are validated by `tests/m012_s01_override_guard_test.py -v` and `OVERRIDE_DENIED` ledger assertions in the runbook.
- EMERGENCY_HOLD entry/exit transitions and forbidden paths are validated by `tests/m012_s01_emergency_hold_test.py -v` and the runbook cleanup sequence.
- Auditability and time-bound behavior are verified operationally via Postgres checks in `scripts/verify_m012_s01.sh` and ledger entries containing `guard_assertion_id=INV-SPS-EMERG-001`.

## Requirement Changes

- R034: active → validated — proved by `tests/m012_s01_override_guard_test.py -v`, `tests/m012_s01_emergency_hold_test.py -v`, and `scripts/verify_m012_s01.sh`.

## Forward Intelligence

### What the next milestone should know
- The emergency/override runbook provisions docker-compose and tears it down; re-run `scripts/start_temporal_dev.sh` before ad-hoc DB inspections.

### What's fragile
- Review decision signaling in the runbook may log workflow-not-found warnings when cases are seeded directly in Postgres; this is expected but can confuse log-only checks.

### Authoritative diagnostics
- `case_transition_ledger` rows with `event_type='OVERRIDE_DENIED'` and `guard_assertion_id=INV-SPS-EMERG-001` are the definitive enforcement signal.

### What assumptions changed
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
