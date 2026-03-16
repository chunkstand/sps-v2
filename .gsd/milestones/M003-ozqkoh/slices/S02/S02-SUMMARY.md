---
id: S02
parent: M003-ozqkoh
milestone: M003-ozqkoh
provides:
  - subject_author_id required field on CreateReviewDecisionRequest (fail-closed — no optional skip)
  - _check_reviewer_independence() guard wired first in create_review_decision (before idempotency check and any DB op)
  - 403 denial with guard_assertion_id=INV-SPS-REV-001 and normalized_business_invariants=["INV-008"] on self-approval
  - WARNING log reviewer_api.independence_denied on all denials
  - reviewer_independence_status="PASS" in DB row on accepted decisions
  - Integration tests proving both denial path (no DB row) and acceptance path (PASS in DB)
  - S01 test POST bodies updated with subject_author_id to avoid 422 regression
requires:
  - slice: S01
    provides: POST /api/v1/reviews/decisions endpoint, CreateReviewDecisionRequest model, get_normalized_business_invariants wiring, S01 integration test infrastructure
affects:
  - S03
  - S04
key_files:
  - src/sps/api/routes/reviews.py
  - tests/m003_s02_reviewer_independence_test.py
  - tests/m003_s01_reviewer_api_boundary_test.py
key_decisions:
  - Guard call placed after decision_received log and before idempotency check — earliest point before any DB operation
  - get_normalized_business_invariants("INV-SPS-REV-001") used in denial response (not hardcoded invariant list)
  - subject_author_id is required, not optional — fail-closed with no skip path
  - _seed_permit_case() helper added to success-path test to satisfy review_decisions FK constraint; denial test never reaches INSERT so no seed needed
  - Helpers inlined in S02 test rather than imported from S01 to avoid inter-test coupling
patterns_established:
  - Independence guard as a pure helper (_check_reviewer_independence) that raises or returns None — no side effects beyond log + raise
  - Integration tests that exercise only a guard seed only the minimal required DB rows rather than standing up a Temporal worker
observability_surfaces:
  - WARNING log: reviewer_api.independence_denied reviewer_id=... subject_author_id=... guard_assertion_id=INV-SPS-REV-001
  - 403 response body: {"detail": {"error": "REVIEW_INDEPENDENCE_DENIED", "guard_assertion_id": "INV-SPS-REV-001", "normalized_business_invariants": ["INV-008"]}}
  - docker compose logs api | grep independence_denied — surfaces denied self-approval attempts
  - SELECT decision_id, reviewer_independence_status FROM review_decisions WHERE case_id = '...'; — no row on denial, PASS on success
drill_down_paths:
  - .gsd/milestones/M003-ozqkoh/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S02/tasks/T02-SUMMARY.md
duration: ~25m
verification_result: passed
completed_at: 2026-03-15
---

# S02: Reviewer independence policy guard

**Self-approval on POST /api/v1/reviews/decisions returns 403 with stable guard/invariant IDs and zero DB writes; distinct-reviewer decisions succeed with reviewer_independence_status=PASS.**

## What Happened

T01 added `subject_author_id: str = Field(min_length=1)` to `CreateReviewDecisionRequest` and wired `_check_reviewer_independence(reviewer_id, subject_author_id)` as the first call inside `create_review_decision` — after the `decision_received` log, before the idempotency check and every DB operation. When the IDs match, the guard logs `reviewer_api.independence_denied` at WARNING (with both IDs and the guard assertion ID) and raises `HTTPException(403)` with a body containing `REVIEW_INDEPENDENCE_DENIED`, `guard_assertion_id=INV-SPS-REV-001`, and the invariant list sourced from `get_normalized_business_invariants("INV-SPS-REV-001")` — not hardcoded. All three POST bodies in the S01 test were updated to include `"subject_author_id": "author-of-the-case"` (distinct from each `reviewer_id`) to avoid a 422 regression from the new required field.

T02 created `tests/m003_s02_reviewer_independence_test.py` with two integration tests. The denial test POSTs with `reviewer_id == subject_author_id`, asserts 403 with the correct `guard_assertion_id` and `normalized_business_invariants`, and then queries Postgres to confirm no `review_decisions` row was written. The success test adds a `_seed_permit_case()` helper (required to satisfy the FK constraint when the INSERT actually runs), POSTs with distinct IDs, asserts 201, and queries Postgres to confirm `reviewer_independence_status='PASS'`. The seed helper is only called in the success test — the denial test never reaches the INSERT. Signal failure (no Temporal worker) is expected and does not fail the success-path test.

## Verification

```
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s
# → 2 passed in 0.73s

pytest tests/ -k "not (integration or temporal)" -x -q
# → 9 passed, 7 skipped in 0.64s (no regressions)
```

Slice-level checks:
- ✅ Self-approval → 403 + `guard_assertion_id=INV-SPS-REV-001` + `normalized_business_invariants=["INV-008"]` + no DB row
- ✅ Distinct reviewer → 201 + `reviewer_independence_status=PASS` in Postgres
- ✅ Unit-only pytest → no regressions (S01 test bodies updated)

## Requirements Advanced

- R007 — Independence guard now enforced end-to-end with stable identifiers; moving to validated

## Requirements Validated

- R007 — Proved: self-approval denied 403 with `guard_assertion_id=INV-SPS-REV-001` + `INV-008` + no DB row; distinct-reviewer accepted 201 with `PASS` in DB, against real Postgres

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 added `_seed_permit_case()` helper not mentioned in the plan. Required because the success test reaches the DB INSERT which has a FK constraint on `permit_cases.case_id`. The denial test (the focus of the no-DB-write check) did not need it. This is within the plan's intended scope.

## Known Limitations

- Independence check is purely `reviewer_id == subject_author_id`; rolling-quarter threshold metrics and org-level conflict detection are deferred to a later milestone per Decision #27.
- No exception/override path exists — denials are fail-closed with no bypass. This is intentional per Decision #24.

## Follow-ups

- none

## Files Created/Modified

- `src/sps/api/routes/reviews.py` — added `subject_author_id` field, `_check_reviewer_independence()` helper, guard call in `create_review_decision`
- `tests/m003_s02_reviewer_independence_test.py` — new; two integration tests proving denial and acceptance paths
- `tests/m003_s01_reviewer_api_boundary_test.py` — added `"subject_author_id"` to all three POST body dicts

## Forward Intelligence

### What the next slice should know
- The guard assertion registry (`get_normalized_business_invariants`) is already wired and working — S03 can use it for `INV-SPS-CONTRA-001` the same way S02 uses it for `INV-SPS-REV-001`.
- The `_seed_permit_case()` pattern (insert minimal parent rows before exercising a guard that reaches INSERT) will be needed in S03 and S04 tests as well.
- `_reset_db()` truncates all tables in reverse FK order — verify the contradiction/dissent tables are included once those migrations land.

### What's fragile
- `subject_author_id` is a plain string — no validation against an actual user registry. Passing an arbitrary string satisfies the guard; real author identity enforcement is deferred.
- Signal delivery after the independence guard passes is still best-effort (same as S01). A denied decision that somehow reached signal delivery would have the same best-effort behavior, but the guard prevents any DB write so recovery is trivial.

### Authoritative diagnostics
- `docker compose logs api | grep independence_denied` — surfaces denied attempts with both IDs; trustworthy because the log is emitted before any DB operation
- `SELECT decision_id, reviewer_independence_status FROM review_decisions WHERE case_id = '...';` — confirms no row on denial, PASS on success; ground truth is Postgres
- 403 `detail.guard_assertion_id` field — stable identifier; if it's missing or wrong, the guard registration in `guard-assertions.yaml` has changed
