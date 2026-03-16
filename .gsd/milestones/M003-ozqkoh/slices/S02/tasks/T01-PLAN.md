---
estimated_steps: 5
estimated_files: 2
---

# T01: Add independence guard to reviewer endpoint and update S01 test

**Slice:** S02 — Reviewer independence policy guard  
**Milestone:** M003-ozqkoh

## Description

Add `subject_author_id` as a required field to `CreateReviewDecisionRequest` and wire `_check_reviewer_independence()` into `create_review_decision` before the idempotency check. The guard must raise `HTTPException(403)` with stable guard/invariant IDs sourced from `get_normalized_business_invariants("INV-SPS-REV-001")`. Update the S01 integration test to include `subject_author_id` in all POST bodies so it continues to pass validation under the new required field.

## Steps

1. Import `get_normalized_business_invariants` from `sps.guards.guard_assertions` at the top of `reviews.py`.
2. Add `subject_author_id: str = Field(min_length=1)` to `CreateReviewDecisionRequest` (after `reviewer_id`).
3. Add `_check_reviewer_independence(reviewer_id: str, subject_author_id: str) -> None` helper:
   - If `reviewer_id == subject_author_id`, emit `logger.warning("reviewer_api.independence_denied reviewer_id=%s subject_author_id=%s guard_assertion_id=INV-SPS-REV-001", reviewer_id, subject_author_id)` and raise `HTTPException(status_code=403, detail={"error": "REVIEW_INDEPENDENCE_DENIED", "guard_assertion_id": "INV-SPS-REV-001", "normalized_business_invariants": get_normalized_business_invariants("INV-SPS-REV-001")})`.
   - If not equal, return `None` (allow through).
4. In `create_review_decision`, call `_check_reviewer_independence(req.reviewer_id, req.subject_author_id)` as the first statement (before the idempotency check and before any DB operation).
5. In `tests/m003_s01_reviewer_api_boundary_test.py`, add `"subject_author_id": "author-of-the-case"` to all POST body dicts where `"reviewer_id"` is set. The `subject_author_id` must differ from `reviewer_id` so the guard passes.

## Must-Haves

- [ ] `subject_author_id: str = Field(min_length=1)` present in `CreateReviewDecisionRequest` (required, not optional)
- [ ] `_check_reviewer_independence` helper exists; returns `None` on pass, raises `HTTPException(403)` on match
- [ ] `get_normalized_business_invariants("INV-SPS-REV-001")` used in denial response — not hardcoded `["INV-008"]`
- [ ] Guard is the first statement in `create_review_decision` (before idempotency check)
- [ ] `reviewer_api.independence_denied` warning log emitted with `reviewer_id`, `subject_author_id`, `guard_assertion_id`
- [ ] All POST body dicts in `m003_s01_reviewer_api_boundary_test.py` include `subject_author_id` distinct from `reviewer_id`
- [ ] `pytest tests/ -k "not (integration or temporal)" -x -q` passes

## Verification

- `python -c "from sps.api.routes.reviews import _check_reviewer_independence; print('ok')"` → ok
- `python -c "from sps.api.routes.reviews import CreateReviewDecisionRequest; m = CreateReviewDecisionRequest.model_fields; assert 'subject_author_id' in m; print('field present')"` → field present
- `pytest tests/ -k "not (integration or temporal)" -x -q` → passes with no new failures

## Observability Impact

- Signals added/changed: `reviewer_api.independence_denied reviewer_id=... subject_author_id=... guard_assertion_id=INV-SPS-REV-001` — WARNING level, emitted before any DB operation
- How a future agent inspects this: `docker compose logs api | grep independence_denied` surfaces denied self-approval attempts; 403 body contains `guard_assertion_id` for stable identification
- Failure state exposed: 403 response body with `error=REVIEW_INDEPENDENCE_DENIED`, `guard_assertion_id`, `normalized_business_invariants`

## Inputs

- `src/sps/api/routes/reviews.py` — current S01 endpoint; add field + guard helper + guard call
- `src/sps/guards/guard_assertions.py` — `get_normalized_business_invariants()` function to import
- `tests/m003_s01_reviewer_api_boundary_test.py` — update POST bodies to include `subject_author_id`

## Expected Output

- `src/sps/api/routes/reviews.py` — `CreateReviewDecisionRequest` has `subject_author_id`; `_check_reviewer_independence()` helper wired at top of `create_review_decision`
- `tests/m003_s01_reviewer_api_boundary_test.py` — all POST body dicts include `subject_author_id` distinct from `reviewer_id`
