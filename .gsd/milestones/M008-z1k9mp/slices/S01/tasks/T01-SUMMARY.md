---
id: T01
parent: S01
milestone: M008-z1k9mp
provides:
  - reviewer queue + evidence summary endpoints with integration tests
key_files:
  - src/sps/api/contracts/reviews.py
  - src/sps/api/routes/reviews.py
  - tests/m008_s01_reviewer_queue_evidence_test.py
key_decisions:
  - Evidence summary responses include review decision summaries with independence status.
patterns_established:
  - Union-based evidence ID aggregation with a single metadata fetch per case.
observability_surfaces:
  - reviewer_api.queue_fetched / reviewer_api.evidence_summary structured log lines
  - GET /api/v1/reviews/queue
  - GET /api/v1/reviews/cases/{case_id}/evidence-summary
  - HTTP 401/404 error payloads
duration: 2h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add reviewer queue + evidence summary endpoints with tests

**Shipped reviewer queue/evidence summary API contracts with integration coverage and structured logs.**

## What Happened
- Added reviewer queue/evidence response contracts (queue items, artifact metadata, review decision summaries).
- Implemented `/api/v1/reviews/queue` and `/api/v1/reviews/cases/{case_id}/evidence-summary` with evidence aggregation + single artifact lookup per case.
- Added structured log lines for queue/evidence fetches and verified via logger capture in tests.
- Built integration tests to cover empty queue, ordering, evidence aggregation, and API key gating.

## Verification
- `. .venv/bin/activate && python -m pytest tests/m008_s01_reviewer_queue_evidence_test.py -v -s`
- `. .venv/bin/activate && python -m pytest tests/m008_s01_reviewer_console_page_test.py -v -s` (fails: file missing; expected for T02)

## Diagnostics
- Call `/api/v1/reviews/queue` with `X-Reviewer-Api-Key` and check `reviewer_api.queue_fetched` log line.
- Call `/api/v1/reviews/cases/{case_id}/evidence-summary` and check `reviewer_api.evidence_summary` log line.
- 401/404 responses include `detail.error` codes (`missing_api_key`, `invalid_api_key`, `not_found`).

## Deviations
- None.

## Known Issues
- `tests/m008_s01_reviewer_console_page_test.py` not yet implemented (belongs to T02).

## Files Created/Modified
- `src/sps/api/contracts/reviews.py` — reviewer queue/evidence response models.
- `src/sps/api/routes/reviews.py` — queue + evidence summary endpoints and structured logs.
- `tests/m008_s01_reviewer_queue_evidence_test.py` — integration tests for queue/evidence surfaces.
