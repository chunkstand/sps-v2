# S02: Reviewer Independence Policy Guard — UAT

**Milestone:** M003-ozqkoh  
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: The guard operates entirely within the HTTP layer and Postgres; no human visual experience is required. The integration tests exercise real Postgres and produce durable, inspectable artifacts. The slice plan explicitly states "Human/UAT required: no."

## Preconditions

1. Docker Compose services are running: `docker compose up -d postgres` (Postgres is the minimum; Temporal worker is NOT required for this slice's tests).
2. `SPS_RUN_TEMPORAL_INTEGRATION=1` environment variable is set.
3. Database migrations are applied (the test harness handles this via `_migrate_db()`).
4. `SPS_REVIEWER_API_KEY` is set (test harness provides a dev key inline or via environment).
5. Python virtualenv is active: `.venv/bin/python`.

## Smoke Test

Run the integration test suite for this slice:

```bash
SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m003_s02_reviewer_independence_test.py -v -s
```

**Expected:** `2 passed` — both `test_independence_self_approval_denied_403` and `test_independence_distinct_reviewer_succeeds_201` pass.

## Test Cases

### 1. Self-approval is denied with 403 and stable identifiers (no DB write)

**Purpose:** Verify the independence guard fires before any DB operation when `reviewer_id == subject_author_id`.

1. POST to `POST /api/v1/reviews/decisions` with a valid API key and body where `reviewer_id` and `subject_author_id` are identical (e.g. both `"user-123"`).
2. **Expected HTTP response:** `403 Forbidden`
3. **Expected response body:**
   ```json
   {
     "detail": {
       "error": "REVIEW_INDEPENDENCE_DENIED",
       "guard_assertion_id": "INV-SPS-REV-001",
       "normalized_business_invariants": ["INV-008"]
     }
   }
   ```
4. Query Postgres to confirm no row was written:
   ```sql
   SELECT COUNT(*) FROM review_decisions WHERE case_id = '<case_id_from_body>';
   ```
   **Expected:** `COUNT(*) = 0`
5. Check application logs:
   ```bash
   docker compose logs api | grep independence_denied
   ```
   **Expected:** A WARNING line containing `reviewer_id`, `subject_author_id`, and `guard_assertion_id=INV-SPS-REV-001`.

### 2. Distinct-reviewer decision succeeds with PASS status in DB

**Purpose:** Verify that a decision where `reviewer_id != subject_author_id` passes the guard, is persisted, and has `reviewer_independence_status='PASS'`.

1. Ensure a `permit_cases` row exists for the target `case_id` (the test harness uses `_seed_permit_case()` for this).
2. POST to `POST /api/v1/reviews/decisions` with `reviewer_id` and `subject_author_id` as distinct values (e.g. `"reviewer-456"` and `"author-123"`).
3. **Expected HTTP response:** `201 Created`
4. Query Postgres to confirm the row was written with the correct status:
   ```sql
   SELECT decision_id, reviewer_independence_status
   FROM review_decisions
   WHERE case_id = '<case_id_from_body>';
   ```
   **Expected:** One row with `reviewer_independence_status = 'PASS'`
5. Signal delivery failure (Temporal worker not running) is expected and acceptable — the 201 response is still correct.

### 3. Missing subject_author_id field returns 422

**Purpose:** Verify the field is required and the endpoint is fail-closed (no skip path).

1. POST to `POST /api/v1/reviews/decisions` with a body that omits the `subject_author_id` field entirely.
2. **Expected HTTP response:** `422 Unprocessable Entity`
3. **Expected:** No DB write occurs; Pydantic validation fails before the guard is reached.

### 4. Empty subject_author_id returns 422

**Purpose:** Verify the `min_length=1` constraint is enforced.

1. POST to `POST /api/v1/reviews/decisions` with `"subject_author_id": ""` (empty string).
2. **Expected HTTP response:** `422 Unprocessable Entity`
3. **Expected:** Validation rejects before guard execution.

## Edge Cases

### Guard fires before idempotency check

If the same self-approving request is sent twice (same `idempotency_key`, same matching `reviewer_id == subject_author_id`):

1. Send the self-approving request twice with identical `idempotency_key`.
2. **Expected:** Both requests return `403` — the independence guard fires before the idempotency lookup, so neither request reaches the DB. No 200/409 is returned.

### Stable guard/invariant IDs across restarts

1. Restart the API service: `docker compose restart api`
2. Send a self-approving POST.
3. **Expected:** 403 body still contains `guard_assertion_id=INV-SPS-REV-001` and `normalized_business_invariants=["INV-008"]` — sourced from the guard-assertions registry, not hardcoded.

### Unauthenticated request is rejected before the guard runs

1. POST to `POST /api/v1/reviews/decisions` without the `Authorization: Bearer <key>` header (or with a wrong key).
2. **Expected:** `401 Unauthorized` — API key middleware fires before the independence guard.

## Failure Signals

- `422` instead of `403` on a self-approving request → `subject_author_id` field or guard call is not wired correctly; check `CreateReviewDecisionRequest` model and `create_review_decision` guard placement.
- `201` on a self-approving request → guard is not executing or condition logic is inverted; inspect `_check_reviewer_independence()` in `reviews.py`.
- `403` on a distinct-reviewer request → guard condition is wrong (over-blocking); check the equality comparison in `_check_reviewer_independence()`.
- DB row present after a denied request → guard was raised after DB write; check the call order in `create_review_decision`.
- `reviewer_independence_status` absent or `None` in the success-path DB row → the field default was not set during INSERT; check the `review_decisions` ORM model default.
- `normalized_business_invariants` is `[]` or missing from 403 body → `get_normalized_business_invariants("INV-SPS-REV-001")` returned empty; check `guard-assertions.yaml` for the `INV-SPS-REV-001` entry.

## Requirements Proved By This UAT

- R007 — Reviewer independence/self-approval guard on high-risk surfaces (INV-008): self-approval denied 403 with `guard_assertion_id=INV-SPS-REV-001` + `INV-008` + no DB write; distinct-reviewer accepted 201 with `PASS` in Postgres.

## Not Proven By This UAT

- Rolling-quarter threshold metrics and org-level conflict detection (deferred; not in scope for Phase 3).
- Exception/override path for independence denials (not implemented; intentionally fail-closed per Decision #24).
- S03 contradiction blocking — covered by the next slice.
- S04 dissent artifact persistence — covered by the slice after that.
- Full end-to-end Temporal workflow resume after independence-guarded acceptance (Temporal worker not required for this slice's proof; covered by S01 integration test).

## Notes for Tester

- The Temporal worker does NOT need to be running. Signal delivery failure after an accepted decision is expected and logged as `reviewer_api.signal_failed`; the 201 response is correct regardless.
- The test file is self-contained: it handles DB migration and reset via inline helpers. You do not need to pre-seed data beyond having Postgres reachable.
- If `docker compose logs api | grep independence_denied` shows no output, the log is emitted only for denied (self-approval) requests — run Test Case 1 first to generate a denial before checking logs.
- `guard-assertions.yaml` is the ground truth for what invariants map to `INV-SPS-REV-001`. If the invariant list in a 403 body looks wrong, inspect that file.
