---
estimated_steps: 7
estimated_files: 2
---

# T04: Integration tests and runbook

**Slice:** S03 — Contradiction artifacts + advancement blocking  
**Milestone:** M003-ozqkoh

## Description

Closes R008 by proving all three S03 scenarios against real Postgres. The integration test file mirrors `tests/m003_s02_reviewer_independence_test.py` exactly — same inline helpers, same `asyncio.run(...)` wrapper, same `SPS_RUN_TEMPORAL_INTEGRATION=1` guard. No Temporal worker needed: the contradiction guard is in a DB activity callable as plain Python, and the contradiction API is a standalone HTTP surface.

Three test scenarios:
1. **Blocking contradiction denies advancement** — seed case + ReviewDecision (so denial is definitely from contradiction, not review); POST create blocking contradiction; call `apply_state_transition`; assert `DeniedStateTransitionResult` with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]`.
2. **Resolve allows advancement** — same setup as (1); POST resolve; call `apply_state_transition` with new `request_id`; assert `AppliedStateTransitionResult` with `event_type=CASE_STATE_CHANGED`.
3. **Non-blocking contradiction is transparent** — seed case; POST create contradiction with `blocking_effect=false`; call `apply_state_transition` without a valid `required_review_id`; assert `DeniedStateTransitionResult` with `event_type=APPROVAL_GATE_DENIED` (proves non-blocking contradictions are invisible to the guard).

The runbook (`scripts/verify_m003_s03.sh`) follows the `verify_m003_s01.sh` template but starts only Postgres and the FastAPI server (no worker needed). It drives the full HTTP-API-driven scenario with `curl` and asserts Postgres state with the `assert_postgres` helper.

## Steps

1. Create `tests/m003_s03_contradiction_blocking_test.py`. Add module-level docstring and `SPS_RUN_TEMPORAL_INTEGRATION=1` guard (same pattern as s02). Inline helpers: `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` (TRUNCATE includes `contradiction_artifacts`: `"TRUNCATE TABLE case_transition_ledger, review_decisions, contradiction_artifacts, permit_cases CASCADE"`), `_seed_permit_case`, `_seed_review_decision`.
2. Write helper `_seed_review_decision(case_id, decision_id, outcome="ACCEPT")` — inserts a `ReviewDecision` row directly via `get_sessionmaker()` session, so the contradiction blocking test can confirm denial is from the contradiction guard (not missing review).
3. Write `test_blocking_contradiction_denies_advancement`: call `_reset_db` + `_seed_permit_case(case_id)`; use `httpx.ASGITransport(app=app)` + `AsyncClient` to POST a blocking contradiction to `/api/v1/contradictions` (with `X-Reviewer-Api-Key` header); assert 201; directly call `apply_state_transition(StateTransitionRequest(..., required_review_id=seeded_decision_id, ...))` (after seeding the review); assert result is `DeniedStateTransitionResult`; assert `result.event_type == "CONTRADICTION_ADVANCE_DENIED"`, `result.guard_assertion_id == "INV-SPS-CONTRA-001"`, `result.normalized_business_invariants == ["INV-003"]`.
4. Write `test_resolve_contradiction_allows_advancement`: same seed setup as (3); POST resolve to `/api/v1/contradictions/{contradiction_id}/resolve`; assert 200; call `apply_state_transition` with a fresh `request_id` and the same valid `required_review_id`; assert result is `AppliedStateTransitionResult` with `event_type == "CASE_STATE_CHANGED"`.
5. Write `test_nonblocking_contradiction_is_transparent`: seed case; POST create contradiction with `blocking_effect=false`; call `apply_state_transition` with `required_review_id=None`; assert `DeniedStateTransitionResult` with `event_type == "APPROVAL_GATE_DENIED"`.
6. Create `scripts/verify_m003_s03.sh`. Structure: docker-compose up (Postgres + API), apply migrations, start uvicorn in background, curl create-contradiction (assert 201), curl resolve-contradiction (assert 200), use `assert_postgres` to verify `resolution_status='RESOLVED'` in DB, start a fresh run to prove advancement is now unblocked (requires seeding a review decision directly via `psql` or a helper endpoint). Use cleanup trap. Exit 0 on success.
7. Run the full integration test suite and the runbook; fix any issues.

## Must-Haves

- [ ] All three integration tests pass with `SPS_RUN_TEMPORAL_INTEGRATION=1`.
- [ ] `_reset_db` includes `contradiction_artifacts` in the TRUNCATE.
- [ ] Test (1) verifies `event_type`, `guard_assertion_id`, and `normalized_business_invariants` on the denial result.
- [ ] Test (2) verifies `AppliedStateTransitionResult` with `CASE_STATE_CHANGED` after resolve.
- [ ] Test (3) verifies denial is `APPROVAL_GATE_DENIED` (not `CONTRADICTION_ADVANCE_DENIED`).
- [ ] Runbook exits 0 against docker-compose Postgres.
- [ ] `pytest tests/ -k "not (integration or temporal)" -x -q` still passes.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m003_s03_contradiction_blocking_test.py -v -s` → 3 passed
- `bash scripts/verify_m003_s03.sh` → exits 0
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes

## Observability Impact

- Signals added/changed: test file documents which structured log events to expect (`contradiction_api.create`, `contradiction_api.resolve`, `apply_state_transition` event_type payloads)
- How a future agent inspects this: `SELECT contradiction_id, resolution_status, resolved_at FROM contradiction_artifacts;` and `SELECT event_type, payload FROM case_transition_ledger ORDER BY occurred_at;`
- Failure state exposed: test assertions show exact expected values; runbook uses `assert_postgres` for DB-level assertions

## Inputs

- `tests/m003_s02_reviewer_independence_test.py` — canonical template for inline helpers and test structure
- `src/sps/api/routes/contradictions.py` (T03 output) — endpoints under test
- `src/sps/workflows/permit_case/activities.py` (T02 output) — `apply_state_transition` with contradiction guard
- `src/sps/workflows/permit_case/contracts.py` — `StateTransitionRequest`, `DeniedStateTransitionResult`, `AppliedStateTransitionResult`, `CaseState`
- `scripts/verify_m003_s01.sh` — runbook template
- `scripts/lib/assert_postgres.sh` — `assert_postgres` helper

## Expected Output

- `tests/m003_s03_contradiction_blocking_test.py` — 3 passing integration tests
- `scripts/verify_m003_s03.sh` — operator runbook, exits 0 on success
