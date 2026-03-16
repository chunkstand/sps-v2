# S02: Reviewer independence policy guard

**Goal:** Self-approval on `POST /api/v1/reviews/decisions` is denied with 403 + `guard_assertion_id=INV-SPS-REV-001`; valid distinct-reviewer decisions succeed with `reviewer_independence_status=PASS` in the DB row.

**Demo:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` passes: self-approval returns 403 with stable guard/invariant IDs and no DB write; distinct-reviewer returns 201 with `reviewer_independence_status=PASS`.

## Must-Haves

- `subject_author_id: str` is a **required** field on `CreateReviewDecisionRequest` (fail-closed — no optional skip)
- Guard runs before the idempotency check and before Postgres INSERT; denied decisions produce zero DB writes
- Self-approval returns HTTP 403 with `guard_assertion_id=INV-SPS-REV-001` and `normalized_business_invariants=["INV-008"]` in body
- Guard uses `get_normalized_business_invariants("INV-SPS-REV-001")` — invariant list is not hardcoded
- `reviewer_independence_status="PASS"` in DB row on accepted decision (already set in S01; now evidence-backed)
- S01 integration test updated to include `subject_author_id` (distinct from `reviewer_id`) — avoids 422 regression
- Denial is logged as `reviewer_api.independence_denied` with `reviewer_id`, `subject_author_id`, `guard_assertion_id`
- Integration test proves both paths: 403 denial (no DB row) and 201 success (PASS in DB)

## Proof Level

- This slice proves: contract (independence guard placement and stable denial identifiers)
- Real runtime required: yes (Postgres for DB assertions)
- Human/UAT required: no

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` → 2 passed
- Self-approval test: 403 response + `guard_assertion_id=INV-SPS-REV-001` + `normalized_business_invariants=["INV-008"]` in body + no `review_decisions` row in Postgres
- Distinct-reviewer test: 201 response + `reviewer_independence_status=PASS` in Postgres row
- `pytest tests/ -k "not (integration or temporal)" -x -q` → no regressions (updated S01 test bodies pass validation)

## Observability / Diagnostics

- Runtime signals: `reviewer_api.independence_denied reviewer_id=... subject_author_id=... guard_assertion_id=INV-SPS-REV-001` — new WARNING log emitted before any DB operation on denial
- Inspection surfaces: `SELECT decision_id, reviewer_independence_status FROM review_decisions WHERE case_id = '...';` — confirms no row on denial, `PASS` on success; `docker compose logs api | grep independence_denied` surfaces denied attempts
- Failure visibility: 403 body contains `guard_assertion_id` and `normalized_business_invariants` for stable identification; denial log includes both IDs for correlation
- Redaction constraints: `reviewer_id` and `subject_author_id` are non-sensitive identifiers; safe to log

## Integration Closure

- Upstream surfaces consumed: `src/sps/guards/guard_assertions.py` (existing), `src/sps/api/routes/reviews.py` (S01 output), `tests/m003_s01_reviewer_api_boundary_test.py` (S01 output — needs POST body update)
- New wiring introduced in this slice: `_check_reviewer_independence()` guard wired into `create_review_decision` before idempotency check; `subject_author_id` field added to request model
- What remains before the milestone is truly usable end-to-end: S03 (contradiction blocking), S04 (dissent artifacts)

## Tasks

- [x] **T01: Add independence guard to reviewer endpoint and update S01 test** `est:30m`
  - Why: Implements the self-approval check and makes `subject_author_id` required; fixes the S01 test's 422 regression introduced by the new required field
  - Files: `src/sps/api/routes/reviews.py`, `tests/m003_s01_reviewer_api_boundary_test.py`
  - Do: Add `subject_author_id: str = Field(min_length=1)` to `CreateReviewDecisionRequest`. Add `_check_reviewer_independence(reviewer_id, subject_author_id)` helper that raises `HTTPException(403)` with stable guard/invariant IDs (from `get_normalized_business_invariants`) and logs `reviewer_api.independence_denied`. Call it at the top of `create_review_decision` before the idempotency check. Update all POST body dicts in the S01 test to include `"subject_author_id"` distinct from `"reviewer_id"`.
  - Verify: `python -c "from sps.api.routes.reviews import _check_reviewer_independence; print('ok')"` succeeds; `pytest tests/ -k "not (integration or temporal)" -x -q` passes
  - Done when: `_check_reviewer_independence("same", "same")` raises `HTTPException(403)` with `guard_assertion_id=INV-SPS-REV-001`; S01 test bodies include `subject_author_id`; unit-level pytest passes

- [x] **T02: Write S02 integration tests for both independence paths** `est:25m`
  - Why: Proves the guard operates correctly end-to-end against real Postgres — no DB row on denial, PASS status on accepted decision
  - Files: `tests/m003_s02_reviewer_independence_test.py` (new)
  - Do: Write two tests guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1` using `httpx.ASGITransport(app=app)` + `AsyncClient`. `test_independence_self_approval_denied_403`: POST with `reviewer_id == subject_author_id` → assert 403 + correct guard/invariant IDs + no DB row. `test_independence_distinct_reviewer_succeeds_201`: POST with distinct ids → assert 201 + DB row with `reviewer_independence_status="PASS"`. Signal failure on the success path is expected (no worker running) and must not fail the test. Reuse `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` helpers from S01 test.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` → 2 passed
  - Done when: both tests pass against real Postgres; denial test asserts no DB row; success test asserts `reviewer_independence_status="PASS"`

## Files Likely Touched

- `src/sps/api/routes/reviews.py`
- `tests/m003_s01_reviewer_api_boundary_test.py`
- `tests/m003_s02_reviewer_independence_test.py` (new)
