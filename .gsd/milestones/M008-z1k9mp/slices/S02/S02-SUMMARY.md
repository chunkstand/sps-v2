---
id: S02
parent: M008-z1k9mp
milestone: M008-z1k9mp
provides:
  - rolling-quarter reviewer independence enforcement with subject_author_id persistence
  - docker-compose reviewer runbook covering queue → evidence → decisions with threshold enforcement assertions
requires:
  - slice: S01
    provides: reviewer console MVP (queue + evidence + decision capture)
affects:
  - none
key_files:
  - src/sps/api/routes/reviews.py
  - src/sps/db/models.py
  - alembic/versions/f4c2b1a9d0e3_review_decisions_subject_author_id.py
  - tests/m008_s02_reviewer_independence_thresholds_test.py
  - scripts/verify_m008_s02.sh
key_decisions:
  - repeated pair rate uses (pair_total_reviews - 1) / total_reviews to avoid first-review blocking
  - reset review_decisions between threshold scenarios to keep rolling-quarter rates deterministic
patterns_established:
  - Postgres-backed reviewer independence threshold tests seed history via ReviewDecision rows and real API calls
  - runbook seeds reviewer history with pg_exec + per-scenario truncation and asserts API + Postgres outcomes
observability_surfaces:
  - reviewer_api.independence_warning / reviewer_api.independence_escalation / reviewer_api.independence_blocked logs; 403 guard body includes blocked_reason; review_decisions.subject_author_id + reviewer_independence_status
  - runbook stdout includes reviewer API responses and Postgres summary output
  - Postgres assertions via scripts/lib/assert_postgres.sh
drill_down_paths:
  - .gsd/milestones/M008-z1k9mp/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008-z1k9mp/slices/S02/tasks/T02-SUMMARY.md
duration: 3.5h
verification_result: passed
completed_at: 2026-03-16
---

# S02: Independence thresholds + end-to-end runbook

**Implemented 90-day rolling-window reviewer independence threshold enforcement, persisted status and author linkage, and proved the end-to-end flow via a live docker-compose runbook.**

## What Happened

We added `subject_author_id` to the `ReviewDecision` schema and implemented rolling 90-day reviewer-independence metrics on decision submission. Depending on the repeated pair rate, the system now enforces warning (>25%), escalation (>35%), and block (>50%) thresholds. These states are durably persisted in Postgres and emit structured log events without leaking sensitive notes. When blocked, the system fails closed with a 403 response containing the `INV-SPS-REV-001` guard assertion. 

To prove the integration, we added a complete docker-compose runbook (`scripts/verify_m008_s02.sh`). It boots Postgres, seeds historical reviewer pairings to trigger each threshold, hits the S01 queue and evidence endpoints, submits decisions, and asserts both API responses and live database state.

## Verification

- `pytest tests/m008_s02_reviewer_independence_thresholds_test.py -v -s` — Proved PASS, WARNING, ESCALATION_REQUIRED, and BLOCKED thresholds against real Postgres seeded with historical decisions.
- `bash scripts/verify_m008_s02.sh` — Booted the API + Postgres in docker-compose, fetched the queue and evidence, posted decisions simulating all four threshold outcomes, and verified the database via `psql`.

## Requirements Advanced

- R020 — Reviewer UI queue/evidence view/decision capture is now supported by an end-to-end runbook demonstrating the API flows.
- R021 — Reviewer independence thresholds are computed and enforced with escalation and blocking per spec.

## Requirements Validated

- R020 — Validated via S01 unit tests + S02 docker-compose runbook exercising end-to-end API flows.
- R021 — Validated via integration tests and the S02 docker-compose runbook.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- To keep the integration tests and runbook assertions deterministic without complex date-math mocking, we reset the `review_decisions` table between threshold scenarios.

## Known Limitations

- Thresholds are computed synchronously during decision creation; while sufficient for the current scale, very high volume might eventually warrant an asynchronous rolling rollup.
- The reviewer console UI still relies on API keys and doesn't handle full RBAC or OIDC yet (deferred to M010).

## Follow-ups

- M009 (Observability) will need to ensure the structured log events `reviewer_api.independence_warning/escalation/blocked` are correctly routed to audit sinks.

## Files Created/Modified

- `src/sps/api/routes/reviews.py` — Computed rolling-quarter independence metrics, enforced thresholds, emitted structured logs, persisted status + subject_author_id.
- `src/sps/db/models.py` — Added nullable `subject_author_id` to ReviewDecision.
- `alembic/versions/f4c2b1a9d0e3_review_decisions_subject_author_id.py` — Migration for subject_author_id column.
- `tests/m008_s02_reviewer_independence_thresholds_test.py` — Integration coverage for PASS/WARNING/ESCALATION_REQUIRED/BLOCKED + log assertions.
- `scripts/verify_m008_s02.sh` — End-to-end reviewer runbook with threshold seeding, API calls, and Postgres assertions.

## Forward Intelligence

### What the next slice should know
- The rolling-quarter pair rate calculation uses `(pair_total_reviews - 1) / total_reviews`. This prevents a first-time review pair (1 out of 1 total) from immediately tripping the 100% block threshold. 
- Independence logs intentionally omit notes/dissent text or reviewer comments to respect redaction constraints.

### What's fragile
- The threshold calculation runs a `COUNT(*)` query across the last 90 days per decision submission. It's performant now but lacks an index on `(reviewer_id, subject_author_id, decision_at)`.

### Authoritative diagnostics
- The structured logs (`reviewer_api.independence_blocked`, etc.) and the 403 `INV-SPS-REV-001` response body are the authoritative signals when debugging why a reviewer was denied.
- `review_decisions.reviewer_independence_status` and `review_decisions.subject_author_id` in Postgres are the source of truth for historical enforcement.

### What assumptions changed
- We originally thought we might need to rely on Temporal to enforce independence across concurrent workflows, but handling it synchronously in the FastAPI Postgres transaction proved much simpler and provided immediate fail-closed feedback to the reviewer.