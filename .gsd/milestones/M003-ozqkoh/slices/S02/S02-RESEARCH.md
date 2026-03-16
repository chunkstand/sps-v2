# M003-ozqkoh/S02 — Research

**Date:** 2026-03-16

## Summary

S02 adds a reviewer-independence policy guard to the `POST /api/v1/reviews/decisions` endpoint already built in S01. The guard is narrow and concrete: require a `subject_author_id` field in `CreateReviewDecisionRequest`, treat the review creation surface as high-risk (consistent with surface-map SURF-AUTH-002), and deny with 403 + `guard_assertion_id=INV-SPS-REV-001` + `normalized_business_invariants=[INV-008]` whenever `reviewer_id == subject_author_id` (self-approval). The Postgres row's `reviewer_independence_status` column is updated to `"BLOCKED"` on denial (nothing is written — the request is rejected) and set to `"PASS"` on acceptance. This makes the previously hardcoded `"PASS"` conditional and evidence-backed.

The implementation is a surgical extension of `reviews.py`. The guard runs _before_ the idempotency check and _before_ the Postgres INSERT — a denied decision must never reach the DB or the Temporal signal. The spec maps CTL-11A to `REVIEW_INDEPENDENCE_DENIED`, which is an HTTP 403 (reviewer lacks authority), not a DB ledger event — the audit trail lives in API access logs, not `case_transition_ledger`. No DB migration is required for S02; the `reviewer_independence_status` column already exists.

The integration test must prove two paths: (1) a valid `reviewer_id != subject_author_id` decision succeeds (201, `reviewer_independence_status=PASS` in DB); (2) a self-approval request (`reviewer_id == subject_author_id`) is denied (403, `guard_assertion_id=INV-SPS-REV-001`, no DB row). The test can be non-Temporal (the independence denial happens before the Postgres commit) — both paths are provable with `httpx.ASGITransport(app=app)` + a live Postgres-backed session, no Temporal worker needed for the denial path.

## Recommendation

**Make the change entirely within `src/sps/api/routes/reviews.py`.** Add `subject_author_id: str = Field(min_length=1)` to `CreateReviewDecisionRequest`. Insert a guard function `_check_reviewer_independence(reviewer_id, subject_author_id)` that denies with 403 when they match. Call it at the top of `create_review_decision`, before the idempotency check. Update the `ReviewDecision` INSERT to write `reviewer_independence_status="PASS"` (kept explicit, no change needed for the deny path because we never reach INSERT). Add `subject_author_id` to the response model so callers can verify what was submitted.

Write `tests/m003_s02_reviewer_independence_test.py` with:
- `test_independence_self_approval_denied_403` — same reviewer_id and subject_author_id → 403 + correct guard/invariant IDs, no DB row
- `test_independence_distinct_reviewer_succeeds_201` — different reviewer_id and subject_author_id → 201 + `reviewer_independence_status=PASS` in DB row

The test can run without `SPS_RUN_TEMPORAL_INTEGRATION=1` if Temporal is not needed for the denial path. For the success path, if you want to avoid starting a Temporal workflow, you can insert a synthetic PermitCase row and use the in-process ASGI client — the endpoint won't signal a real workflow if it's not running (signal failure is logged and swallowed). Confirm this approach in the plan and note it explicitly.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Stable denial identifiers | `sps.guards.guard_assertions.get_normalized_business_invariants("INV-SPS-REV-001")` | Returns `["INV-008"]`; avoids hardcoding invariant IDs in the endpoint |
| In-process ASGI test client | `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)` | Established in Decision #30; do not use `httpx.AsyncClient(app=app)` (removed in httpx 0.20) |
| HTTP 403 for reviewer lacks authority | Spec section 10.3 explicitly lists 403 for independence failure; not 422 | Matches the spec error case table and `REVIEW_INDEPENDENCE_DENIED` audit semantics |
| Request model validation | Pydantic v2 `extra="forbid"` already on `CreateReviewDecisionRequest` | Adding `subject_author_id` is a new required field — update existing S01 tests or make it optional with a validator for backward compat |

## Existing Code and Patterns

- `src/sps/api/routes/reviews.py` — the sole file to modify; add `subject_author_id` to request model, add `_check_reviewer_independence()` helper, call it before idempotency check. Pattern: keep the helper pure (returns `None` or raises `HTTPException(403)`), consistent with `require_reviewer_api_key` style.
- `src/sps/guards/guard_assertions.py` — `get_normalized_business_invariants("INV-SPS-REV-001")` returns `["INV-008"]`; use this in the denial response body.
- `invariants/sps/guard-assertions.yaml` — confirms `INV-SPS-REV-001` maps to `["INV-008"]` and is linked to `CTL-11A`. No changes needed.
- `tests/m003_s01_reviewer_api_boundary_test.py` — reference for `httpx.ASGITransport` test pattern, `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` helpers; re-use or import shared fixtures.
- `src/sps/workflows/permit_case/contracts.py` — `ReviewerIndependenceStatus` enum exists (`PASS`, `WARNING`, `ESCALATION_REQUIRED`, `BLOCKED`, `OVERRIDE_APPLIED`); the denial case maps to `BLOCKED`, though since we reject before INSERT this is informational only.

## Constraints

- **Guard placement:** The independence check must run _before_ the idempotency lookup and _before_ the Postgres INSERT. A denied decision must produce zero DB writes. (Spec: CTL-11A is "fail closed" — denial event is `REVIEW_INDEPENDENCE_DENIED`, not a DB ledger row.)
- **No DB migration:** `reviewer_independence_status` column already exists in `review_decisions`. The S02 change is schema-free.
- **subject_author_id is a new required field:** Adding it to `CreateReviewDecisionRequest` is a breaking change for existing callers. The S01 integration test (`m003_s01_reviewer_api_boundary_test.py`) does not include `subject_author_id` in its POST body — it will fail with a 422 validation error after S02 adds it as required. Either make `subject_author_id` optional (with a note that the independence check is skipped when absent — but this violates fail-closed semantics on a high-risk surface), or update the S01 test. The spec's fail-closed requirement argues for making it required and updating S01 tests.
- **403 response shape:** Must include `guard_assertion_id` and `normalized_business_invariants` in the response body for stable denial identification. Match the `DeniedStateTransitionResult` pattern from activities.py conceptually, but return as `HTTPException(403, detail={...})` (not a DB result).
- **Audit trail:** The spec maps `REVIEW_INDEPENDENCE_DENIED` to the reviewer service; this is an API-layer event, not a `case_transition_ledger` row. Structured log `reviewer_api.independence_denied` is the audit surface.
- **Surface classification:** surface-map.yaml lists `SURF-AUTH-002: Review decision creation` as `high_risk: true, requires_reviewer_independence: true`. All `POST /api/v1/reviews/decisions` calls go through this surface — independence check applies unconditionally when `subject_author_id` is present.

## Common Pitfalls

- **Breaking the S01 integration test** — adding `subject_author_id` as required makes existing S01 test POST bodies fail validation. Plan must update `m003_s01_reviewer_api_boundary_test.py` to include the new field (use a different value for reviewer_id and subject_author_id to pass the guard).
- **Fail-open on missing subject_author_id** — if `subject_author_id` is made optional with a "skip check when absent" default, the guard is fail-open on the exact self-approval case INV-008 was designed to catch. This is not acceptable. Make it required, or if optional is chosen for operational reasons, the behavior when absent must be explicit and documented in DECISIONS.
- **Wrong HTTP status** — the spec says 403 (reviewer lacks authority), not 422 (unresolved contradiction/missing evidence) and not 409 (idempotency conflict). Use `HTTPException(status_code=403, ...)`.
- **Logging the subject_author_id in denial** — the structured log should include `reviewer_id`, `subject_author_id` (IDs are not secrets), and `guard_assertion_id`. Don't log the API key (it's never logged anyway).
- **Guard placement after idempotency check** — if the idempotency check runs first, a retried self-approval request might return a 200 (existing row) instead of denying. This would be a correctness bug. Guard must precede the idempotency lookup.

## Open Risks

- **S01 test compatibility:** The S01 tests must be updated to include `subject_author_id`; this is a known dependency noted in S01-SUMMARY Forward Intelligence. Low risk — straightforward one-field addition, but easy to forget.
- **subject_author_id semantics:** The current `CreateReviewDecisionRequest` has no `subject_author_id`. The DB `review_decisions` table also has no `subject_author_id` column. S02 uses it only for the guard check — it does NOT need to persist `subject_author_id`. If future audit requirements demand persistence, that's a future migration. For now: validate in the request, check, discard.
- **ReviewDecisionResponse doesn't expose reviewer_independence_status:** The current `ReviewDecisionResponse` model doesn't include `reviewer_independence_status`. Adding it would allow callers to verify the independence status of the persisted row. Consider whether this is needed for the integration test assertion. Simplest path: query the DB row directly in the test (already done in S01 tests).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` | available (noted in M003 research; not needed for S02 — pure extension) |
| Pydantic v2 | `bobmatnyc/claude-mpm-skills@pydantic` | available (not needed — pattern is established) |

## Sources

- `REVIEW_INDEPENDENCE_DENIED` is the audit event type for CTL-11A; denial returns HTTP 403 (source: spec.md section 10.3 error cases + section 20A guard placement matrix row CTL-11A)
- `INV-SPS-REV-001` maps to `normalized_business_invariants: ["INV-008"]` (source: `invariants/sps/guard-assertions.yaml`)
- Surface SURF-AUTH-002 "Review decision creation" is classified `high_risk: true, requires_reviewer_independence: true` (source: `specs/sps/build-approved/surface-map.yaml`)
- Decision #27 established minimal independence enforcement: require `reviewer_id` + `subject_author_id`, deny when equal (source: `.gsd/DECISIONS.md` row 27)
- S01-SUMMARY Forward Intelligence: `CreateReviewDecisionRequest` has no `subject_author_id`; S02 must add it and update S01 test bodies (source: `.gsd/milestones/M003-ozqkoh/slices/S01/S01-SUMMARY.md`)
- Guard must precede idempotency check and Postgres INSERT — a denied review must produce zero DB side effects (source: CTL-11A "fail closed" semantics + spec section 8.5 forbidden conditions)
