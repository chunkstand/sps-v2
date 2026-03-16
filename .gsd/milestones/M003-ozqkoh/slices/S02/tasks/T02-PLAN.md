---
estimated_steps: 4
estimated_files: 1
---

# T02: Write S02 integration tests for both independence paths

**Slice:** S02 — Reviewer independence policy guard  
**Milestone:** M003-ozqkoh

## Description

Write `tests/m003_s02_reviewer_independence_test.py` with two integration tests that prove the independence guard operates correctly against real Postgres. The denial test posts with matching `reviewer_id == subject_author_id` and asserts 403 + stable guard/invariant IDs + no DB row written. The success test posts with distinct IDs and asserts 201 + `reviewer_independence_status="PASS"` in the persisted DB row. Temporal is not needed for either path (the guard fires before the Postgres INSERT; signal delivery failure is expected and swallowed).

## Steps

1. Create `tests/m003_s02_reviewer_independence_test.py`. Import shared helpers by copying or importing `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` from the S01 test (or inline the same pattern — avoid importing directly to keep tests self-contained and avoid implicit coupling). Guard the module with `SPS_RUN_TEMPORAL_INTEGRATION=1` skip, consistent with S01.
2. Write `test_independence_self_approval_denied_403`:
   - `_wait_for_postgres_ready()`, `_migrate_db()`, `_reset_db()`
   - POST to `/api/v1/reviews/decisions` with a unique `case_id`, `decision_id`, `idempotency_key`; set `reviewer_id == subject_author_id` (e.g. both `"self-reviewer-001"`)
   - Assert `response.status_code == 403`
   - Assert `detail["error"] == "REVIEW_INDEPENDENCE_DENIED"`
   - Assert `detail["guard_assertion_id"] == "INV-SPS-REV-001"`
   - Assert `detail["normalized_business_invariants"] == ["INV-008"]`
   - Query Postgres: `session.get(ReviewDecision, decision_id)` must be `None` (no row written)
3. Write `test_independence_distinct_reviewer_succeeds_201`:
   - `_wait_for_postgres_ready()`, `_migrate_db()`, `_reset_db()`
   - POST with `reviewer_id="reviewer-001"`, `subject_author_id="author-001"` (distinct)
   - Assert `response.status_code == 201`
   - Query Postgres: assert `row.reviewer_independence_status == "PASS"`
   - Signal failure is expected (no Temporal worker); the response is still 201 — assert this explicitly
4. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` and confirm 2 passed.

## Must-Haves

- [ ] Module guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1` skip (consistent with S01)
- [ ] `test_independence_self_approval_denied_403`: 403 status + `error=REVIEW_INDEPENDENCE_DENIED` + `guard_assertion_id=INV-SPS-REV-001` + `normalized_business_invariants=["INV-008"]` + no DB row
- [ ] `test_independence_distinct_reviewer_succeeds_201`: 201 status + `reviewer_independence_status="PASS"` in DB row
- [ ] Uses `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)` (Decision #30 — not `app=` kwarg)
- [ ] FastAPI wraps HTTPException detail in `{"detail": ...}` — test extracts `detail = body.get("detail", body)` before asserting keys
- [ ] Both tests use `asyncio.run(...)` wrapping (consistent with S01 test pattern)
- [ ] `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` → 2 passed

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` → 2 passed
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes (no unit-level regressions)

## Inputs

- `src/sps/api/routes/reviews.py` (T01 output) — must have `subject_author_id` field and `_check_reviewer_independence()` wired
- `tests/m003_s01_reviewer_api_boundary_test.py` — reference for `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db`, `httpx.ASGITransport` pattern
- `sps.db.models.ReviewDecision` — `reviewer_independence_status` column for DB assertion

## Expected Output

- `tests/m003_s02_reviewer_independence_test.py` (new) — two passing integration tests proving denial (403 + no DB row) and acceptance (201 + PASS in DB)
