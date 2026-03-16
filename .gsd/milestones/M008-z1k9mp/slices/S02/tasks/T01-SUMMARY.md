---
id: T01
parent: S02
milestone: M008-z1k9mp
provides:
  - rolling-quarter reviewer independence enforcement with subject_author_id persistence
key_files:
  - src/sps/api/routes/reviews.py
  - src/sps/db/models.py
  - alembic/versions/f4c2b1a9d0e3_review_decisions_subject_author_id.py
  - tests/m008_s02_reviewer_independence_thresholds_test.py
  - .gsd/milestones/M008-z1k9mp/slices/S02/S02-PLAN.md
key_decisions:
  - repeated pair rate uses (pair_total_reviews - 1) / total_reviews to avoid first-review blocking
patterns_established:
  - Postgres-backed reviewer independence threshold tests seed history via ReviewDecision rows and real API calls
observability_surfaces:
  - reviewer_api.independence_warning / reviewer_api.independence_escalation / reviewer_api.independence_blocked logs; 403 guard body includes blocked_reason; review_decisions.subject_author_id + reviewer_independence_status
duration: 2h
verification_result: partial
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Implement rolling-quarter independence enforcement + migration + tests

**Added subject_author_id persistence and rolling-quarter independence threshold enforcement with warning/escalation/blocked logging and deterministic integration tests.**

## What Happened
- Added `subject_author_id` to the ReviewDecision ORM and created a migration on top of the current alembic head.
- Implemented rolling 90-day reviewer-independence metrics in `create_review_decision`, including warning/escalation/blocked thresholds, fail-closed 403 responses with guard assertion metadata, and structured log emission without sensitive notes.
- Added integration tests for PASS/WARNING/ESCALATION_REQUIRED/BLOCKED, seeding review history in Postgres and asserting persisted status + subject_author_id, plus log capture via monkeypatched logger warnings.

## Verification
- `. .venv/bin/activate && SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m008_s02_reviewer_independence_thresholds_test.py -v -s` → **passed (4 tests)**.
- `bash scripts/verify_m008_s02.sh` → **failed** (script missing; expected to land in T02).

## Diagnostics
- Logs: `reviewer_api.independence_warning`, `reviewer_api.independence_escalation`, `reviewer_api.independence_blocked` with pair counts/rate; verified via monkeypatched logger in tests.
- DB inspection: `review_decisions` table now includes `subject_author_id` and `reviewer_independence_status` persisted per decision.
- Failure surface: 403 response detail includes `guard_assertion_id=INV-SPS-REV-001`, `normalized_business_invariants`, and `blocked_reason`.

## Deviations
- None.

## Known Issues
- `scripts/verify_m008_s02.sh` does not exist yet, so slice-level runbook verification is pending T02.

## Files Created/Modified
- `src/sps/api/routes/reviews.py` — compute rolling-quarter independence metrics, enforce thresholds, emit structured logs, persist status + subject_author_id.
- `src/sps/db/models.py` — added nullable `subject_author_id` to ReviewDecision.
- `alembic/versions/f4c2b1a9d0e3_review_decisions_subject_author_id.py` — migration for subject_author_id column.
- `tests/m008_s02_reviewer_independence_thresholds_test.py` — integration coverage for PASS/WARNING/ESCALATION_REQUIRED/BLOCKED + log assertions.
- `.gsd/milestones/M008-z1k9mp/slices/S02/S02-PLAN.md` — marked T01 complete and added diagnostic verification step.
