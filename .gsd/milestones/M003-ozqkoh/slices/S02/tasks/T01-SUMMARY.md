---
id: T01
parent: S02
milestone: M003-ozqkoh
provides:
  - subject_author_id required field on CreateReviewDecisionRequest
  - _check_reviewer_independence() guard wired first in create_review_decision
  - S01 test POST bodies updated with subject_author_id
key_files:
  - src/sps/api/routes/reviews.py
  - tests/m003_s01_reviewer_api_boundary_test.py
key_decisions:
  - Guard call placed after the decision_received log and before the idempotency check — earliest possible point before any DB operation
  - Used get_normalized_business_invariants("INV-SPS-REV-001") in denial response (not hardcoded); resolves from guard-assertions.yaml at runtime
patterns_established:
  - Independence guard as a pure helper (_check_reviewer_independence) that raises or returns None — no side effects beyond log + raise
observability_surfaces:
  - WARNING log: reviewer_api.independence_denied reviewer_id=... subject_author_id=... guard_assertion_id=INV-SPS-REV-001
  - 403 response body: {error: REVIEW_INDEPENDENCE_DENIED, guard_assertion_id: INV-SPS-REV-001, normalized_business_invariants: [...]}
  - docker compose logs api | grep independence_denied — surfaces denied self-approval attempts
duration: ~10m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Add independence guard to reviewer endpoint and update S01 test

**Added `subject_author_id` required field and `_check_reviewer_independence()` guard to the reviewer endpoint; updated S01 test POST bodies to include the new field.**

## What Happened

- Imported `get_normalized_business_invariants` from `sps.guards.guard_assertions` in `reviews.py`.
- Added `subject_author_id: str = Field(min_length=1)` to `CreateReviewDecisionRequest` after `reviewer_id`.
- Wrote `_check_reviewer_independence(reviewer_id, subject_author_id)` helper: when IDs match, logs `reviewer_api.independence_denied` at WARNING with all three IDs and raises `HTTPException(403)` with `REVIEW_INDEPENDENCE_DENIED` error, `guard_assertion_id=INV-SPS-REV-001`, and `normalized_business_invariants` sourced from the registry. Returns `None` otherwise.
- Wired the call as the first statement inside `create_review_decision` (after the `decision_received` log, before the idempotency check and any DB operation).
- Updated all three POST body dicts in `tests/m003_s01_reviewer_api_boundary_test.py` to include `"subject_author_id": "author-of-the-case"` — distinct from each `reviewer_id` value so the guard passes.

## Verification

- `python -c "from sps.api.routes.reviews import _check_reviewer_independence; print('ok')"` → `ok`
- `python -c "from sps.api.routes.reviews import CreateReviewDecisionRequest; m = CreateReviewDecisionRequest.model_fields; assert 'subject_author_id' in m; print('field present')"` → `field present`
- `pytest tests/ -k "not (integration or temporal)" -x -q` → **9 passed, 6 skipped** — no regressions

Slice-level checks status:
- `pytest tests/ -k "not (integration or temporal)" -x -q` → ✅ passes (updated S01 test bodies pass validation)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` → ⏳ pending (test file created in T02)

## Diagnostics

- Denial path: `docker compose logs api | grep independence_denied` — WARNING line includes `reviewer_id`, `subject_author_id`, `guard_assertion_id`
- 403 response body shape: `{"detail": {"error": "REVIEW_INDEPENDENCE_DENIED", "guard_assertion_id": "INV-SPS-REV-001", "normalized_business_invariants": ["INV-008"]}}`
- Guard placement confirmed by reading `create_review_decision`: independence check on line 218, idempotency query starts line 221

## Deviations

None. Followed the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `src/sps/api/routes/reviews.py` — added import, `subject_author_id` field, `_check_reviewer_independence()` helper, guard call in `create_review_decision`
- `tests/m003_s01_reviewer_api_boundary_test.py` — added `"subject_author_id": "author-of-the-case"` to all three POST body dicts
