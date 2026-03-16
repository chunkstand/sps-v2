---
estimated_steps: 5
estimated_files: 4
---
# T01: Add reviewer queue + evidence summary endpoints with tests

**Slice:** S01 — Reviewer console MVP (queue + evidence + decision capture)
**Milestone:** M008-z1k9mp

## Description
Define reviewer queue and evidence summary API surfaces (gated by reviewer API key), wire them to authoritative Postgres models, and prove the contract with integration tests. This establishes the data backbone the console will consume and advances R020 while preparing R021 by surfacing existing independence status fields.

## Steps
1. Add reviewer queue/evidence response models under `src/sps/api/contracts/reviews.py` (queue item, evidence summary, artifact metadata).
2. Implement `/api/v1/reviews/queue` and `/api/v1/reviews/cases/{case_id}/evidence-summary` in `src/sps/api/routes/reviews.py`, aggregating evidence IDs across case-linked tables and fetching artifact metadata in a single query per case.
3. Add structured log lines for queue/evidence fetch with counts and case_id (no evidence payloads or reviewer notes).
4. Create `tests/m008_s01_reviewer_queue_evidence_test.py` to seed minimal rows and assert queue ordering, empty-state behavior, and evidence aggregation results.
5. Run the test file to verify behavior and adjust response shapes as needed.

## Must-Haves
- [ ] Reviewer queue returns REVIEW_PENDING cases with case + project summary fields and is gated by the reviewer API key.
- [ ] Evidence summary returns aggregated evidence IDs + metadata for a case without N+1 queries (single evidence lookup per request).

## Verification
- `pytest tests/m008_s01_reviewer_queue_evidence_test.py -v -s`
- Inspect response payloads in the test assertions for counts, ordering, and evidence metadata.

## Observability Impact
- Signals added/changed: reviewer queue/evidence fetch log lines with case_id and counts.
- How a future agent inspects this: call `/api/v1/reviews/queue` or `/api/v1/reviews/cases/{case_id}/evidence-summary` with the reviewer API key; check logs for count entries.
- Failure state exposed: HTTP 401/404/500 error payloads with error codes in response bodies.

## Inputs
- `src/sps/api/routes/reviews.py` — existing reviewer API patterns and auth dependency.
- `src/sps/db/models.py` — authoritative case/evidence tables for aggregation.

## Expected Output
- `src/sps/api/contracts/reviews.py` — new response models for queue/evidence.
- `src/sps/api/routes/reviews.py` — reviewer queue and evidence summary endpoints.
- `tests/m008_s01_reviewer_queue_evidence_test.py` — integration tests proving the contract.
