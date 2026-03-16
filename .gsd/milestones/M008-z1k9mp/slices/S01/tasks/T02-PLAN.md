---
estimated_steps: 4
estimated_files: 4
---
# T02: Serve reviewer console MVP and wire decision submission

**Slice:** S01 — Reviewer console MVP (queue + evidence + decision capture)
**Milestone:** M008-z1k9mp

## Description
Add a minimal reviewer console entrypoint (`/reviewer`) using Jinja2 templates and vanilla JS to call the reviewer queue/evidence endpoints and submit decisions to the real reviewer API. This closes the UI loop for R020 and enables manual reviewer walkthroughs.

## Steps
1. Create a reviewer console route module (e.g., `src/sps/api/routes/reviewer_console.py`) that renders a Jinja2 template for `/reviewer`.
2. Add a template (`src/sps/api/templates/reviewer_console.html`) with queue, evidence, and decision panels plus an API key input.
3. Implement inline JS to fetch queue/evidence data and POST decisions, showing success/error banners (including guard denial payloads) without logging sensitive inputs.
4. Add `tests/m008_s01_reviewer_console_page_test.py` to assert `/reviewer` returns HTML with stable anchors (ids/classes) and that the page loads without template errors.

## Must-Haves
- [ ] `/reviewer` is served by the FastAPI app and renders the console shell.
- [ ] Decision submission posts to the real reviewer API with required fields and surfaces API responses (including independence guard denials) in the UI.

## Verification
- `pytest tests/m008_s01_reviewer_console_page_test.py -v -s`
- Manual smoke: run the API, open `/reviewer`, load queue, view evidence, submit a decision with the reviewer API key.

## Observability Impact
- Signals added/changed: client-side error banner shows HTTP status + response body; no new server log noise beyond normal access logs.
- How a future agent inspects this: visit `/reviewer` in a browser and use devtools network panel for failed requests.
- Failure state exposed: visible error banner on the console when API calls fail.

## Inputs
- `src/sps/api/main.py` — router mounting entrypoint for the reviewer console.
- `src/sps/api/routes/reviews.py` — queue/evidence/decision endpoints to call.

## Expected Output
- `src/sps/api/routes/reviewer_console.py` — reviewer console route definition.
- `src/sps/api/templates/reviewer_console.html` — console UI template + JS.
- `tests/m008_s01_reviewer_console_page_test.py` — HTML contract test.
