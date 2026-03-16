---
id: T03
parent: S01
milestone: M009-ct4p0u
provides:
  - /ops Jinja dashboard with client-side metrics fetch
key_files:
  - src/sps/api/routes/ops.py
  - src/sps/api/main.py
  - src/sps/api/templates/ops/index.html
  - src/sps/api/static/ops.js
  - tests/m009_s01_dashboard_test.py
key_decisions:
  - Split ops routes into authenticated API router and unauthenticated page router to keep /ops render accessible while preserving API auth.
patterns_established:
  - Jinja template passes metrics endpoint via data attribute consumed by static JS.
observability_surfaces:
  - /ops status panel + console.error("ops.dashboard.metrics_fetch_failed") on fetch failures.
duration: 1.2h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Render `/ops` dashboard page wired to metrics API

**Shipped a new /ops Jinja dashboard with static JS polling the ops metrics endpoint and rendering queue health cards.**

## What Happened

Added a dedicated `/ops` page router that renders a new Jinja template under `src/sps/api/templates/ops/index.html` and mounted a static directory for `ops.js`. The UI uses a minimal ops aesthetic, includes an API key input/refresh control, and renders queue depth, contradiction backlog, and stalled review counts from `/api/v1/ops/dashboard/metrics`. The JS logs fetch failures and updates the status panel. Dashboard tests now assert the HTML render, static JS availability, and the metrics endpoint wiring.

## Verification

- `.venv/bin/python -m pytest tests/m009_s01_dashboard_test.py` (skipped: SPS_RUN_TEMPORAL_INTEGRATION not set).
- `.venv/bin/python -m pytest tests/m009_s01_audit_events_test.py` (skipped: SPS_RUN_TEMPORAL_INTEGRATION not set).
- Browser smoke: started `.venv/bin/uvicorn sps.api.main:app --port 8000`, loaded `/ops`, entered API key, refreshed metrics, and confirmed "Last refresh" status with metric cards rendered.

## Diagnostics

- `/ops` shows a status panel with fetch status; client logs `ops.dashboard.metrics_fetch_failed` on fetch failures.
- `/api/v1/ops/dashboard/metrics` remains the metrics source for queue depth, contradiction backlog, and stalled review counts.

## Deviations

- Template and static assets live under `src/sps/api/templates/ops` and `src/sps/api/static` (matching existing reviewer console layout) instead of the `src/sps/templates`/`src/sps/static` paths in the task plan.
- Added `page_router` in `ops.py` to avoid applying reviewer API key dependencies to the HTML route.

## Known Issues

- Integration tests are env-gated and were skipped because SPS_RUN_TEMPORAL_INTEGRATION is unset.

## Files Created/Modified

- `src/sps/api/routes/ops.py` — added `/ops` page route and shared templates configuration.
- `src/sps/api/main.py` — mounted static assets and included ops page router.
- `src/sps/api/templates/ops/index.html` — new ops dashboard Jinja template.
- `src/sps/api/static/ops.js` — metrics fetch/render logic with failure logging.
- `tests/m009_s01_dashboard_test.py` — dashboard render + static asset assertions.
