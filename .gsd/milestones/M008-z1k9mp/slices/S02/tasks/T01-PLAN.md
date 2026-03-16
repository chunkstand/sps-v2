---
estimated_steps: 7
estimated_files: 5
---

# T01: Implement rolling-quarter independence enforcement + migration + tests

**Slice:** S02 — Independence thresholds + end-to-end runbook
**Milestone:** M008-z1k9mp

## Description
Add persisted author identity for review decisions, compute rolling-quarter reviewer independence metrics, enforce warning/escalation/blocked status with fail-closed behavior, and prove the policy via deterministic tests.

## Steps
1. Add `subject_author_id` to the ReviewDecision ORM model and generate an alembic migration to add the column (nullable for existing rows).
2. Extend reviewer decision creation to persist `subject_author_id` from the request and compute 90-day UTC independence metrics before insert.
3. Implement threshold evaluation for WARNING/ESCALATION_REQUIRED/BLOCKED with structured logs and fail-closed 403 when blocked.
4. Add tests covering PASS/WARNING/ESCALATION_REQUIRED/BLOCKED with seeded history and verify persisted status and guard responses.

## Must-Haves
- [ ] ReviewDecision rows store `subject_author_id` and computed `reviewer_independence_status`.
- [ ] Independence thresholds compute over a 90-day UTC window and deny with guard assertion `INV-SPS-REV-001` when blocked.
- [ ] Structured logs emit warning/escalation/blocked signals without leaking reviewer notes.

## Verification
- `. .venv/bin/activate && python -m pytest tests/m008_s02_reviewer_independence_thresholds_test.py -v -s`
- Inspect DB rows in test to confirm persisted status and subject_author_id.

## Observability Impact
- Signals added/changed: `reviewer_api.independence_warning`, `reviewer_api.independence_escalation`, `reviewer_api.independence_blocked` structured logs.
- How a future agent inspects this: query `review_decisions` status/subject_author_id; check logs for threshold events.
- Failure state exposed: 403 response includes guard assertion/invariant IDs and blocked reason.

## Inputs
- `src/sps/api/routes/reviews.py` — current reviewer decision flow + self-approval guard placement.
- `src/sps/db/models.py` — ReviewDecision schema definition.

## Expected Output
- `src/sps/api/routes/reviews.py` — rolling-quarter independence enforcement and logging.
- `src/sps/db/models.py` + `alembic/versions/*` — persisted subject_author_id.
- `tests/m008_s02_reviewer_independence_thresholds_test.py` — policy coverage for all threshold outcomes.
