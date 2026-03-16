---
estimated_steps: 5
estimated_files: 4
---
# T02: Expose ops metrics API for queue/contradiction/stalled counts

**Slice:** S01 — Audit Events and Minimal Dashboards
**Milestone:** M009-ct4p0u

## Description
Provide a structured ops metrics endpoint that returns queue depth, contradiction backlog, and stalled review counts backed by Postgres queries.

## Steps
1. Add query helpers to compute queue depth, contradiction backlog, and stalled review counts.
2. Define a response schema/service wrapper for the metrics payload.
3. Implement `GET /api/v1/ops/dashboard/metrics` returning the structured metrics.
4. Add an integration test seeding data and asserting metric fields and counts.

## Must-Haves
- [ ] Query helpers return queue depth, contradiction backlog, and stalled review counts.
- [ ] Metrics endpoint returns a stable JSON schema with timestamps.
- [ ] Integration test validates metrics values against seeded fixtures.

## Verification
- `pytest tests/m009_s01_dashboard_test.py`
- Response includes all expected fields with non-null values.

## Observability Impact
- Signals added/changed: metrics response payload for queue/backlog/stalled counts.
- How a future agent inspects this: `GET /api/v1/ops/dashboard/metrics` or test fixtures.
- Failure state exposed: missing fields or zero counts when fixtures exist.

## Inputs
- `src/sps/db/models/*` — existing case/review/contradiction tables used by metrics queries.

## Expected Output
- `src/sps/db/queries/ops_metrics.py` — metric query helpers.
- `src/sps/services/ops_metrics.py` — response assembly helper.
- `src/sps/api/routes/ops.py` — metrics endpoint.
- `tests/m009_s01_dashboard_test.py` — API integration test.
