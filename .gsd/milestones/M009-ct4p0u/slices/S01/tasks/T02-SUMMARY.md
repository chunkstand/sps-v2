---
id: T02
parent: S01
milestone: M009-ct4p0u
provides:
  - ops metrics endpoint for queue depth, contradiction backlog, and stalled reviews
key_files:
  - src/sps/db/queries/ops_metrics.py
  - src/sps/services/ops_metrics.py
  - src/sps/api/routes/ops.py
  - src/sps/api/main.py
  - tests/m009_s01_dashboard_test.py
key_decisions:
  - None
patterns_established:
  - Ops metrics assembled via query helpers + service response builder
observability_surfaces:
  - GET /api/v1/ops/dashboard/metrics
  - ops_metrics.snapshot structured log line
  - Postgres contradiction_artifacts and permit_cases counts
duration: 0.7h
verification_result: failed (pytest missing)
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Expose ops metrics API for queue/contradiction/stalled counts

**Added ops metrics query helpers, service response builder, and the /api/v1/ops/dashboard/metrics endpoint with integration coverage.**

## What Happened
- Added query helpers for queue depth, contradiction backlog, and stalled review counts.
- Added OpsMetricsResponse schema + builder with a stable timestamped payload.
- Exposed GET /api/v1/ops/dashboard/metrics behind reviewer API key authentication.
- Added integration test that seeds cases/contradictions and asserts metric counts + timestamps.

## Verification
- `pytest tests/m009_s01_dashboard_test.py` (failed: pytest not installed in current environment)
- `python -m pytest tests/m009_s01_dashboard_test.py` (failed: python not available)
- `python3 -m pytest tests/m009_s01_dashboard_test.py` (failed: pytest module missing)
- `python3 -m pytest tests/m009_s01_audit_events_test.py` (failed: pytest module missing)

## Diagnostics
- Call `GET /api/v1/ops/dashboard/metrics` with `X-Reviewer-Api-Key` header to inspect counts + timestamps.
- Logs include `ops_metrics.snapshot queue_depth=... contradiction_backlog=... stalled_review_count=...`.

## Deviations
- None.

## Known Issues
- Verification is blocked because pytest is not installed in the current environment.

## Files Created/Modified
- `src/sps/db/queries/__init__.py` — created queries package.
- `src/sps/db/queries/ops_metrics.py` — query helpers for ops metrics counts.
- `src/sps/services/__init__.py` — created services package.
- `src/sps/services/ops_metrics.py` — response schema and metrics assembly helper.
- `src/sps/api/routes/ops.py` — ops metrics API endpoint.
- `src/sps/api/main.py` — registered ops router.
- `tests/m009_s01_dashboard_test.py` — integration test for metrics endpoint.
