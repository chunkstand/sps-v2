---
id: T02
parent: S01
milestone: M008-z1k9mp
provides:
  - Reviewer console route + Jinja2 template with queue/evidence/decision JS wiring
key_files:
  - src/sps/api/routes/reviewer_console.py
  - src/sps/api/templates/reviewer_console.html
  - src/sps/api/main.py
  - tests/m008_s01_reviewer_console_page_test.py
  - pyproject.toml
key_decisions:
  - None
patterns_established:
  - Jinja2 template entrypoint for simple console shells
observability_surfaces:
  - Reviewer console error banner showing HTTP status + response payload
  - /reviewer UI for manual inspection
duration: 1.1h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Serve reviewer console MVP and wire decision submission

**Added a styled reviewer console at /reviewer with JS wiring for queue, evidence, and decision submission.**

## What Happened
- Added a reviewer console router and mounted it in the FastAPI app.
- Built a Jinja2 template with queue, evidence, and decision capture panels plus inline JS for API calls and error/success banners.
- Added Jinja2 runtime dependency and a contract test to assert the console shell renders with stable anchors.
- Verified client-side error banner shows HTTP status + payload when queue fetch fails.

## Verification
- `.venv/bin/python -m pytest tests/m008_s01_reviewer_console_page_test.py -v -s`
- `.venv/bin/python -m pytest tests/m008_s01_reviewer_queue_evidence_test.py -v -s`
- Browser: loaded `http://127.0.0.1:8000/reviewer`, asserted key panels/submit button, triggered queue fetch to see `HTTP 401` error banner.

## Diagnostics
- Visit `/reviewer` and click **Load Queue** to surface HTTP status + body in the error banner.
- Use `/api/v1/reviews/queue` and `/api/v1/reviews/cases/{case_id}/evidence-summary` to inspect backend data feeding the UI.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/api/routes/reviewer_console.py` — reviewer console route with Jinja2 template rendering.
- `src/sps/api/templates/reviewer_console.html` — console UI shell, styling, and JS wiring.
- `src/sps/api/main.py` — mounted reviewer console router.
- `tests/m008_s01_reviewer_console_page_test.py` — HTML contract test for `/reviewer`.
- `pyproject.toml` — added Jinja2 dependency for template rendering.
