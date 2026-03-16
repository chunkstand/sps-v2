---
estimated_steps: 5
estimated_files: 4
---
# T03: Render `/ops` dashboard page wired to metrics API

**Slice:** S01 — Audit Events and Minimal Dashboards
**Milestone:** M009-ct4p0u

## Description
Serve a minimal Jinja-based `/ops` dashboard and wire client-side JS to render the metrics returned by the ops endpoint.

## Steps
1. Add `/ops` route + template render in the ops router.
2. Create a minimal Jinja template with metric placeholders and status text.
3. Add a small JS file that fetches metrics and updates the DOM.
4. Extend dashboard tests to assert the page renders and pulls metrics.

## Must-Haves
- [ ] `/ops` route returns a rendered HTML page without server errors.
- [ ] JS fetches `/api/v1/ops/dashboard/metrics` and renders counts.
- [ ] Dashboard test validates render + metrics fetch behavior.

## Verification
- `pytest tests/m009_s01_dashboard_test.py`
- `/ops` renders and displays queue depth, contradiction backlog, and stalled review counts.

## Observability Impact
- Signals added/changed: UI shows metrics values; frontend logs on fetch failures.
- How a future agent inspects this: open `/ops` page or run dashboard test.
- Failure state exposed: missing metrics or fetch error in response.

## Inputs
- `src/sps/api/routes/ops.py` — ops router used by metrics endpoint.
- `src/sps/services/ops_metrics.py` — metrics payload used by JS.

## Expected Output
- `src/sps/templates/ops/index.html` — Jinja template for `/ops`.
- `src/sps/static/ops.js` — client JS for metrics rendering.
- `tests/m009_s01_dashboard_test.py` — UI render/assertions.
