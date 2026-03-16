---
id: T02
parent: S02
milestone: M003-ozqkoh
provides:
  - tests/m003_s02_reviewer_independence_test.py — two passing integration tests proving denial (403 + no DB row) and acceptance (201 + PASS in DB)
key_files:
  - tests/m003_s02_reviewer_independence_test.py
key_decisions:
  - _seed_permit_case() helper added to satisfy review_decisions FK constraint (case_id → permit_cases) in the success test; the denial test never reaches INSERT so no seed needed there
  - Self-contained helpers (_wait_for_postgres_ready, _migrate_db, _reset_db, _seed_permit_case) inlined rather than imported from S01 to avoid inter-test coupling
  - Uses httpx.ASGITransport(app=app) + AsyncClient(transport=...) per Decision #30 (not app= kwarg)
  - asyncio.run(...) wrapping for both sync test entry points — consistent with S01 pattern
patterns_established:
  - Integration tests that only exercise a guard (not the full workflow) seed only the minimal required DB rows rather than standing up a Temporal worker
observability_surfaces:
  - Denial detection: `docker compose logs api | grep independence_denied` — WARNING line includes reviewer_id, subject_author_id, guard_assertion_id
  - DB audit: `SELECT decision_id, reviewer_independence_status FROM review_decisions WHERE case_id = '...';` — no row on denial, PASS on success
  - 403 body shape: {"detail": {"error": "REVIEW_INDEPENDENCE_DENIED", "guard_assertion_id": "INV-SPS-REV-001", "normalized_business_invariants": ["INV-008"]}}
duration: ~15min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Write S02 integration tests for both independence paths

**Two integration tests prove the independence guard operates correctly against real Postgres: self-approval → 403 + no DB row; distinct reviewer → 201 + PASS in DB.**

## What Happened

Created `tests/m003_s02_reviewer_independence_test.py` with two tests guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1` (consistent with S01). The denial test (self-approval) hit 403 cleanly on the first run. The success test initially failed with a FK violation — `review_decisions.case_id` references `permit_cases`, and the distinct-reviewer test reaches the INSERT (guard passes), so a parent permit_case row must exist. Added `_seed_permit_case()` helper to insert a minimal PermitCase row before the POST. Both tests then passed on the second run.

Key structural choices:
- Helpers are inlined (not imported from S01) to keep the test self-contained
- `_seed_permit_case` is only called in the success test; the denial test never reaches the INSERT so no seed is needed
- Signal delivery failure is explicit: the test comments that no Temporal worker is running and asserts 201 is still returned (swallowed per the route's best-effort contract)

## Verification

```
SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m003_s02_reviewer_independence_test.py -v -s
# → 2 passed in 0.73s

.venv/bin/pytest tests/ -k "not (integration or temporal)" -x -q
# → 9 passed, 7 skipped in 0.71s (no regressions)
```

Slice-level verification:
- ✅ `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` → 2 passed
- ✅ Self-approval test: 403 + guard_assertion_id=INV-SPS-REV-001 + normalized_business_invariants=["INV-008"] + no DB row
- ✅ Distinct-reviewer test: 201 + reviewer_independence_status=PASS in Postgres row
- ✅ `pytest tests/ -k "not (integration or temporal)" -x -q` → no regressions

## Diagnostics

- Denial log: `docker compose logs api | grep independence_denied` — WARNING includes `reviewer_id`, `subject_author_id`, `guard_assertion_id=INV-SPS-REV-001`
- DB state: `SELECT decision_id, reviewer_independence_status FROM review_decisions WHERE case_id = '...';`
  - Denial path: no row
  - Success path: row with `reviewer_independence_status='PASS'`
- 403 body: `{"detail": {"error": "REVIEW_INDEPENDENCE_DENIED", "guard_assertion_id": "INV-SPS-REV-001", "normalized_business_invariants": ["INV-008"]}}`

## Deviations

- Added `_seed_permit_case()` helper not mentioned in the plan — required because the success test reaches the DB INSERT, which has a FK constraint on `permit_cases.case_id`. The denial test (plan's focus for no-DB-write check) did not need it.

## Known Issues

none

## Files Created/Modified

- `tests/m003_s02_reviewer_independence_test.py` — new; two integration tests proving denial (403 + no DB row) and acceptance (201 + PASS in DB)
