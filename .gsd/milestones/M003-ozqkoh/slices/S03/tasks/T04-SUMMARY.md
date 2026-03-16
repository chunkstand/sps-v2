---
id: T04
parent: S03
milestone: M003-ozqkoh
provides:
  - 3 passing integration tests in tests/m003_s03_contradiction_blocking_test.py covering all S03 scenarios
  - Operator runbook scripts/verify_m003_s03.sh — exits 0 against docker-compose Postgres
key_files:
  - tests/m003_s03_contradiction_blocking_test.py
  - scripts/verify_m003_s03.sh
key_decisions:
  - _seed_review_decision inserts ReviewDecision directly via ORM (not via HTTP API) with all required non-nullable fields (schema_version, object_type, object_id, dissent_flag, decision_at) to avoid needing a running API for test seeding
  - Runbook seeds PermitCase + ReviewDecision via python -c (inline script) instead of psql to avoid COPY/INSERT syntax complexity for JSONB and boolean fields
  - Boolean psql assertion uses "t" (the raw psql -A -t output for true) not "true"
  - Runbook omits Temporal entirely — all assertions against case_transition_ledger are driven by apply_state_transition called directly via python -c
patterns_established:
  - _seed_review_decision helper: direct ORM insert with all required ReviewDecision fields — reusable pattern for tests needing a valid review gate bypass
  - asyncio.run() wrapping pattern for async test functions mirrors s02 exactly
  - Runbook Python seeding pattern: inline heredoc python -c with sys.path.insert + env overrides, avoids psql DDL friction
observability_surfaces:
  - SELECT contradiction_id, resolution_status, resolved_at FROM contradiction_artifacts WHERE case_id='...'
  - SELECT event_type, payload FROM case_transition_ledger WHERE case_id='...' ORDER BY occurred_at
  - GET /api/v1/contradictions/{id} — read-only endpoint for contradiction artifact state
  - Test assertions document exact expected field values for CONTRADICTION_ADVANCE_DENIED events
duration: ~15 min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T04: Integration tests and runbook

**3 S03 integration tests pass and the runbook exits 0 against docker-compose Postgres.**

## What Happened

Created `tests/m003_s03_contradiction_blocking_test.py` mirroring the s02 pattern — same inline helpers, same `asyncio.run()` wrapper, same `SPS_RUN_TEMPORAL_INTEGRATION=1` guard. Three test scenarios:

1. `test_blocking_contradiction_denies_advancement` — seeds case + ReviewDecision (so the review gate would pass if no contradiction existed), POSTs a blocking contradiction, calls `apply_state_transition` directly, asserts `DeniedStateTransitionResult` with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]`. Also asserts the ledger row in Postgres has the correct payload fields.

2. `test_resolve_contradiction_allows_advancement` — same seed, confirms first advancement is denied, POSTs resolve, then calls `apply_state_transition` with a fresh `request_id`, asserts `AppliedStateTransitionResult` with `event_type=CASE_STATE_CHANGED`. DB-verified: `resolution_status=RESOLVED`, `resolved_at` non-null, `resolved_by=reviewer-test`, `case_state=APPROVED_FOR_SUBMISSION`.

3. `test_nonblocking_contradiction_is_transparent` — seeds case only (no review decision), POSTs contradiction with `blocking_effect=false`, calls `apply_state_transition` without a valid review_id, asserts `DeniedStateTransitionResult` with `event_type=APPROVAL_GATE_DENIED` and `guard_assertion_id != INV-SPS-CONTRA-001`.

`_seed_review_decision` helper required all non-nullable ReviewDecision fields (including `schema_version`, `object_type`, `object_id`, `dissent_flag`, `decision_at`) — discovered by reading the ORM model directly rather than the s02 test which always seeded via HTTP.

The runbook `scripts/verify_m003_s03.sh` drives the full scenario via HTTP + `apply_state_transition` Python invocation:
- Postgres up, migrations applied, FastAPI server started
- Seed via inline Python script (avoids psql quoting/JSONB friction)
- POST create → 201, assert DB row, POST resolve → 200, assert RESOLVED, assert advancement succeeds with `CASE_STATE_CHANGED` in ledger
- GET artifact → 200, 401 on missing/wrong key, 409 on duplicate create

Two minor fixes during runbook iteration: `mktemp` template had `.json` suffix (macOS requires X's at end), and boolean assertion needed `"t"` not `"true"` (psql `-A -t` mode).

## Verification

```
SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m003_s03_contradiction_blocking_test.py -v -s
# → 3 passed in 0.71s

pytest tests/ -k "not (integration or temporal)" -x -q
# → 9 passed, 8 skipped in 0.68s (no regressions)

bash scripts/verify_m003_s03.sh
# → exits 0, runbook: ok
```

All slice verification criteria pass.

## Diagnostics

After T04:
- `SELECT contradiction_id, blocking_effect, resolution_status, resolved_at, resolved_by FROM contradiction_artifacts WHERE case_id='...';` — shows artifact lifecycle
- `SELECT event_type, payload FROM case_transition_ledger WHERE case_id='...' ORDER BY occurred_at;` — shows `CONTRADICTION_ADVANCE_DENIED` payload with `guard_assertion_id` and `normalized_business_invariants`
- `GET /api/v1/contradictions/{id}` — inspect contradiction state without DB access
- `docker compose logs api | grep contradiction_api` — structured log events for create/resolve

## Deviations

- `_seed_review_decision` uses direct ORM insert (not HTTP API) — required to avoid starting a full API client within the sync seeder. All required ReviewDecision fields populated explicitly.
- Runbook uses `python -c` inline script for seeding and `apply_state_transition` invocation instead of a standalone helper script — simpler, no additional script to maintain.

## Known Issues

none

## Files Created/Modified

- `tests/m003_s03_contradiction_blocking_test.py` — 3 integration tests for S03 scenarios (blocking denial, resolve allows, non-blocking transparent)
- `scripts/verify_m003_s03.sh` — operator runbook for S03, exits 0 against docker-compose Postgres
