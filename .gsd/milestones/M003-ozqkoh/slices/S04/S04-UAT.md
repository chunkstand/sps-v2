# S04: Dissent artifacts — UAT

**Milestone:** M003-ozqkoh  
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All observable behavior is DB state + HTTP responses against a live Postgres instance. No Temporal worker is required. The runbook (`scripts/verify_m003_s04.sh`) exercises the complete flow; the integration test covers the same scenarios in-process. Together they prove R009 without gap.

## Preconditions

1. Docker Compose stack is running with `postgres` service healthy: `docker compose up -d postgres`
2. Alembic migrations applied through `d8e2a4c9b1f5`: `alembic upgrade head`
3. API server started: `uvicorn sps.api.main:app --port 8000` (or via runbook)
4. `SPS_REVIEWER_API_KEY` is set (dev default: `dev-reviewer-key`)
5. A `permit_cases` row exists for the `case_id` used in requests (required by FK constraint on `review_decisions`)

For automated verification, run instead:
```
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s
# or
bash scripts/verify_m003_s04.sh
```

## Smoke Test

```bash
curl -s -X POST http://localhost:8000/api/v1/reviews/decisions \
  -H "X-Reviewer-Api-Key: dev-reviewer-key" \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "D-SMOKE-001",
    "idempotency_key": "idem/D-SMOKE-001",
    "case_id": "<seeded_case_id>",
    "reviewer_id": "REV-001",
    "subject_author_id": "AUTHOR-001",
    "outcome": "ACCEPT_WITH_DISSENT",
    "dissent_scope": "structural",
    "dissent_rationale": "Smoke test dissent"
  }'
```

**Expected:** HTTP 201 + `dissent_artifact_id` field non-null (`"DISSENT-D-SMOKE-001"`).

## Test Cases

### 1. ACCEPT_WITH_DISSENT creates linked dissent artifact

1. POST to `POST /api/v1/reviews/decisions` with `X-Reviewer-Api-Key: dev-reviewer-key`, body:
   ```json
   {
     "decision_id": "D-AWD-001",
     "idempotency_key": "idem/D-AWD-001",
     "case_id": "<seeded_case_id>",
     "reviewer_id": "REV-A",
     "subject_author_id": "AUTHOR-B",
     "outcome": "ACCEPT_WITH_DISSENT",
     "dissent_scope": "structural",
     "dissent_rationale": "Concerns about load path calculations",
     "dissent_required_followup": "Re-submit with stamped PE review"
   }
   ```
2. **Expected:** HTTP 201; response body includes `"dissent_artifact_id": "DISSENT-D-AWD-001"`, `"outcome": "ACCEPT_WITH_DISSENT"`.
3. Extract `dissent_artifact_id` from response (e.g. `DISSENT-D-AWD-001`).
4. GET `http://localhost:8000/api/v1/dissents/DISSENT-D-AWD-001` with `X-Reviewer-Api-Key: dev-reviewer-key`.
5. **Expected:** HTTP 200; response body:
   ```json
   {
     "dissent_id": "DISSENT-D-AWD-001",
     "linked_review_id": "D-AWD-001",
     "case_id": "<seeded_case_id>",
     "scope": "structural",
     "rationale": "Concerns about load path calculations",
     "required_followup": "Re-submit with stamped PE review",
     "resolution_state": "OPEN",
     "created_at": "<timestamp>"
   }
   ```
6. Confirm `resolution_state` is `"OPEN"` (new artifacts always start OPEN).
7. Confirm DB row via psql: `SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts WHERE dissent_id = 'DISSENT-D-AWD-001';` → one row returned.

### 2. ACCEPT decision creates no dissent artifact

1. POST to `POST /api/v1/reviews/decisions` with `X-Reviewer-Api-Key: dev-reviewer-key`, body:
   ```json
   {
     "decision_id": "D-ACC-001",
     "idempotency_key": "idem/D-ACC-001",
     "case_id": "<seeded_case_id>",
     "reviewer_id": "REV-A",
     "subject_author_id": "AUTHOR-B",
     "outcome": "ACCEPT"
   }
   ```
2. **Expected:** HTTP 201; response body includes `"dissent_artifact_id": null`, `"outcome": "ACCEPT"`.
3. Confirm no dissent row via psql: `SELECT COUNT(*) FROM dissent_artifacts WHERE linked_review_id = 'D-ACC-001';` → `0`.
4. Attempt GET `http://localhost:8000/api/v1/dissents/DISSENT-D-ACC-001` with `X-Reviewer-Api-Key: dev-reviewer-key`.
5. **Expected:** HTTP 404; response body `{"error": "not_found", "dissent_id": "DISSENT-D-ACC-001"}`.

### 3. Observability signal fires for ACCEPT_WITH_DISSENT

1. Run the accept-with-dissent scenario from Test Case 1 with API logs visible (e.g. uvicorn stdout or `docker compose logs api`).
2. Inspect logs for line containing `reviewer_api.dissent_artifact_created`.
3. **Expected:** Log line with fields `dissent_id`, `linked_review_id`, `case_id`, `scope_len` — does NOT contain the raw scope or rationale text.

### 4. Auth check on GET /api/v1/dissents

1. GET `http://localhost:8000/api/v1/dissents/DISSENT-D-AWD-001` with NO `X-Reviewer-Api-Key` header.
2. **Expected:** HTTP 401.
3. GET same URL with wrong key (`X-Reviewer-Api-Key: wrong-key`).
4. **Expected:** HTTP 401.

## Edge Cases

### Missing dissent fields on ACCEPT_WITH_DISSENT

1. POST to `POST /api/v1/reviews/decisions` with `outcome=ACCEPT_WITH_DISSENT` but omit `dissent_scope` and `dissent_rationale`:
   ```json
   {
     "decision_id": "D-BAD-001",
     "idempotency_key": "idem/D-BAD-001",
     "case_id": "<seeded_case_id>",
     "reviewer_id": "REV-A",
     "subject_author_id": "AUTHOR-B",
     "outcome": "ACCEPT_WITH_DISSENT"
   }
   ```
2. **Expected:** HTTP 422; response body lists Pydantic validation error with message "dissent_scope and dissent_rationale are required when outcome is ACCEPT_WITH_DISSENT". No DB row created.

### Missing only dissent_scope

1. POST with `outcome=ACCEPT_WITH_DISSENT`, `dissent_rationale` present, `dissent_scope` absent.
2. **Expected:** HTTP 422; same validation error.

### Missing only dissent_rationale

1. POST with `outcome=ACCEPT_WITH_DISSENT`, `dissent_scope` present, `dissent_rationale` absent.
2. **Expected:** HTTP 422; same validation error.

### ACCEPT with dissent fields supplied (fields silently ignored)

1. POST with `outcome=ACCEPT`, `dissent_scope="irrelevant"`, `dissent_rationale="irrelevant"`.
2. **Expected:** HTTP 201; `dissent_artifact_id=null`; no dissent row in DB. Optional dissent fields are ignored when outcome is not ACCEPT_WITH_DISSENT.

### GET unknown dissent_id

1. GET `http://localhost:8000/api/v1/dissents/DISSENT-DOES-NOT-EXIST` with valid key.
2. **Expected:** HTTP 404; `{"error": "not_found", "dissent_id": "DISSENT-DOES-NOT-EXIST"}`.

### Atomic rollback on commit failure

1. (Diagnostic/observable only — cannot easily force in normal ops.) If `db.commit()` fails after both rows are queued: neither the `ReviewDecision` nor the `DissentArtifact` row persists. DB remains clean; endpoint returns 500. API logs will contain `reviewer_api.decision_commit_failed` at ERROR level with `decision_id` and `exc_type`.

## Failure Signals

- HTTP 422 on POST with ACCEPT_WITH_DISSENT but no dissent fields → validation working correctly; if NOT returned, `model_validator` is not registered
- HTTP 201 on POST with ACCEPT_WITH_DISSENT but `dissent_artifact_id` is null → INSERT block in `create_review_decision` not firing; check `row.dissent_flag` in DB
- `ForeignKeyViolation fk_dissent_artifacts_linked_review_id` in postgres logs → `db.flush()` missing or removed from ACCEPT_WITH_DISSENT branch in `reviews.py`
- `reviewer_api.dissent_artifact_created` absent in logs for ACCEPT_WITH_DISSENT → log statement removed or `dissent_flag` is False in the ReviewDecision row
- GET /api/v1/dissents/{id} returns 404 for a recently-created artifact → check `dissent_id` format: should be `DISSENT-{decision_id}` (e.g. `DISSENT-D-AWD-001`), not the bare `decision_id`
- `ImportError` on `from sps.api.routes.dissents import router` → check `dissents.py` for missing imports or syntax errors

## Requirements Proved By This UAT

- R009 — Dissent artifacts recorded and queryable: ACCEPT_WITH_DISSENT decisions create a durable `dissent_artifacts` row linked to the originating `ReviewDecision`, with `resolution_state=OPEN`; the artifact is queryable by `dissent_id`; ACCEPT decisions produce no dissent row. Both scenarios proven by integration test + operator runbook against real Postgres.

## Not Proven By This UAT

- Resolution state lifecycle (`OPEN → RESOLVED` transition) — no resolution endpoint exists yet; deferred to release gate milestone
- Release-blocking enforcement acting on `resolution_state` — explicitly deferred
- Dissent artifact list endpoints (by case or reviewer) — not implemented; only point lookup by dissent_id
- Dissent behavior when Temporal signal delivery fails — not exercised (Temporal not required for this slice)

## Notes for Tester

- The `dissent_id` is always derived as `DISSENT-{decision_id}` — if your `decision_id` is `D-AWD-001`, the `dissent_id` is `DISSENT-D-AWD-001`. The `GET /api/v1/dissents/` prefix is at `/api/v1/dissents/`, not `/api/v1/reviews/dissents/`.
- `required_followup` is nullable; omitting it in the POST body is valid even for ACCEPT_WITH_DISSENT.
- The `SPS_RUN_TEMPORAL_INTEGRATION=1` flag is required for the pytest integration tests to run (they make real Postgres connections and will be skipped without it).
- If the `dissent_artifacts` table doesn't exist, run `alembic upgrade head` — migration `d8e2a4c9b1f5` creates it.
