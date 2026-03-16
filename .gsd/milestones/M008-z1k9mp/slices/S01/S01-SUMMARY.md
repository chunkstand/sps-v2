---
id: S01
parent: M008-z1k9mp
milestone: M008-z1k9mp
provides:
  - reviewer console MVP (queue + evidence + decision capture)
requires:
  - slice: none
    provides: n/a
affects:
  - S02
key_files:
  - src/sps/api/contracts/reviews.py
  - src/sps/api/routes/reviews.py
  - src/sps/api/routes/reviewer_console.py
  - src/sps/api/templates/reviewer_console.html
  - src/sps/api/main.py
  - tests/m008_s01_reviewer_queue_evidence_test.py
  - tests/m008_s01_reviewer_console_page_test.py
  - pyproject.toml
key_decisions:
  - Evidence summary responses include review decision summaries with reviewer independence status.
patterns_established:
  - Union-based evidence ID aggregation with a single metadata fetch per case.
  - Jinja2 template entrypoint for minimal reviewer consoles (no frontend toolchain).
observability_surfaces:
  - reviewer_api.queue_fetched structured log event
  - reviewer_api.evidence_summary structured log event
  - GET /api/v1/reviews/queue
  - GET /api/v1/reviews/cases/{case_id}/evidence-summary
  - GET /reviewer (UI error banner for API failures)
drill_down_paths:
  - .gsd/milestones/M008-z1k9mp/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008-z1k9mp/slices/S01/tasks/T02-SUMMARY.md
duration: 3.1h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Reviewer console MVP (queue + evidence + decision capture)

**Reviewer queue/evidence APIs and a FastAPI-served console now let reviewers browse pending cases and submit decisions against the real reviewer API.**

## What Happened
- Shipped reviewer queue and evidence summary endpoints with stable response contracts, evidence aggregation, and structured log events.
- Added a `/reviewer` console served via Jinja2 with inline JS to fetch queue/evidence data and submit decisions, including API error surfacing.
- Added integration/contract tests to prove queue/evidence behavior and console shell anchors.

## Verification
- `. .venv/bin/activate && python -m pytest tests/m008_s01_reviewer_queue_evidence_test.py -v -s`
- `. .venv/bin/activate && python -m pytest tests/m008_s01_reviewer_console_page_test.py -v -s`

## Requirements Advanced
- R020 — Delivered reviewer queue/evidence endpoints plus a reviewer console shell that submits decisions through the reviewer API; integration/contract tests pass.

## Requirements Validated
- None.

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- None.

## Known Limitations
- Rolling-quarter independence thresholds and enforcement signals are deferred to S02.
- No live docker-compose runbook yet for the reviewer console flow.

## Follow-ups
- Implement rolling-quarter independence threshold computation + enforcement signals (S02).
- Produce the live docker-compose runbook and UAT coverage (S02).

## Files Created/Modified
- `src/sps/api/contracts/reviews.py` — reviewer queue/evidence response contracts.
- `src/sps/api/routes/reviews.py` — queue/evidence endpoints with aggregation + logs.
- `src/sps/api/routes/reviewer_console.py` — reviewer console router.
- `src/sps/api/templates/reviewer_console.html` — console UI shell + inline JS wiring.
- `src/sps/api/main.py` — mounted reviewer console router.
- `tests/m008_s01_reviewer_queue_evidence_test.py` — integration tests for queue/evidence.
- `tests/m008_s01_reviewer_console_page_test.py` — HTML contract test for `/reviewer`.
- `pyproject.toml` — added Jinja2 dependency.

## Forward Intelligence
### What the next slice should know
- Evidence summary responses already include review decision summaries (with independence status), so the UI can render decision context without extra calls.
- The console expects the reviewer API key to be entered in the UI and passed as `X-Reviewer-Api-Key` on fetches.

### What's fragile
- Evidence aggregation depends on the union of multiple case-linked tables; future schema changes need to update the aggregation list to avoid missing artifacts.

### Authoritative diagnostics
- `/api/v1/reviews/queue` + `reviewer_api.queue_fetched` log events are the quickest signal for queue data correctness.
- `/api/v1/reviews/cases/{case_id}/evidence-summary` + `reviewer_api.evidence_summary` logs confirm aggregation output and counts.

### What assumptions changed
- Assumed a frontend build toolchain might be needed; Jinja2 + vanilla JS proved sufficient for the MVP console.
