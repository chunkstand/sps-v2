# S01: Audit Events and Minimal Dashboards — UAT

**Milestone:** M009-ct4p0u
**Written:** 2026-03-16

## UAT Type
- UAT mode: mixed
- Why this mode is sufficient: The slice is proven via Postgres-backed integration tests, and the operator-facing `/ops` UI requires a live API + browser verification.

## Preconditions
- Postgres is running and reachable with the configured `SPS_DB_URL`.
- Migrations are applied: `alembic upgrade head`.
- API server is running: `.venv/bin/uvicorn sps.api.main:app --port 8000`.
- Reviewer API key is available in `SPS_REVIEWER_API_KEY`.

## Smoke Test
Open `http://localhost:8000/ops`, enter the reviewer API key, click refresh, and confirm the queue health cards render without errors.

## Test Cases
### 1. Ops dashboard renders and fetches metrics
1. Navigate to `http://localhost:8000/ops`.
2. Enter the reviewer API key in the input and click **Refresh**.
3. **Expected:** Status panel shows a recent refresh timestamp and the three metric cards render numeric values.

### 2. Ops metrics endpoint returns structured counts
1. Seed a few cases/contradictions (or use the integration test seed helpers) and call:
   - `curl -H "X-Reviewer-Api-Key: $SPS_REVIEWER_API_KEY" http://localhost:8000/api/v1/ops/dashboard/metrics`
2. **Expected:** JSON includes `queue_depth`, `contradiction_backlog`, `stalled_review_count`, `generated_at`, `stalled_review_before`, and `stalled_review_threshold_hours` with non-null values.

### 3. Audit event emitted for review decision
1. Create a permit case (use any existing case fixture or seed one manually).
2. Post a review decision:
   - `curl -X POST http://localhost:8000/api/v1/reviews/decisions \
     -H "X-Reviewer-Api-Key: $SPS_REVIEWER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"decision_id":"DEC-UAT-1","idempotency_key":"idem/DEC-UAT-1","case_id":"CASE-UAT-1","reviewer_id":"reviewer-uat","subject_author_id":"author-uat","outcome":"ACCEPT"}'`
3. Query Postgres:
   - `SELECT action, correlation_id, request_id FROM audit_events WHERE request_id = 'DEC-UAT-1';`
4. **Expected:** One row with `action='review_decision.created'` and `correlation_id='CASE-UAT-1'`.

## Edge Cases
### Missing or invalid reviewer API key
1. Call the metrics endpoint without the `X-Reviewer-Api-Key` header.
2. **Expected:** 401 response; `/ops` shows a failed refresh state and console logs `ops.dashboard.metrics_fetch_failed`.

## Failure Signals
- `/ops` returns non-200 or displays empty cards after refresh.
- Metrics endpoint missing required fields or returns null timestamps.
- No `audit_events` row exists after a successful review decision.

## Requirements Proved By This UAT
- R022 — Audit event persistence is observable via Postgres query after a review decision.
- R023 — Dashboard + metrics endpoint surfaces queue, contradiction backlog, and stalled review counts.

## Not Proven By This UAT
- Release bundle gating and rollback rehearsal requirements (R024–R026).

## Notes for Tester
- The `/ops` page is unauthenticated, but the metrics API requires the reviewer API key until M010 auth/RBAC lands.
- If the dashboard fetch fails, check the browser console for `ops.dashboard.metrics_fetch_failed` and verify the API key.
