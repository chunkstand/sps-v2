# S02: Independence thresholds + end-to-end runbook

**Goal:** Enforce rolling-quarter reviewer independence thresholds with persisted status + escalation/denial signals, and prove the reviewer console → API → Postgres flow via a live docker-compose runbook.
**Demo:** Run `scripts/verify_m008_s02.sh` to boot docker-compose, seed threshold history, fetch reviewer queue/evidence, submit decisions, and observe WARNING/ESCALATION_REQUIRED/BLOCKED enforcement against live Postgres.

## Must-Haves
- Rolling-quarter independence thresholds computed in UTC and persisted on ReviewDecision rows with WARNING/ESCALATION_REQUIRED/BLOCKED statuses per spec.
- Enforcement emits structured warning/escalation/blocked signals and fails closed (403 + guard assertion) when thresholds block.
- A docker-compose runbook exercises reviewer console + API + Postgres end-to-end, including threshold enforcement behavior.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: yes

## Verification
- `. .venv/bin/activate && python -m pytest tests/m008_s02_reviewer_independence_thresholds_test.py -v -s`
- `bash scripts/verify_m008_s02.sh`
- Inspect blocked response payload/logs to confirm 403 includes guard assertion `INV-SPS-REV-001` and structured log event `reviewer_api.independence_blocked` emits without reviewer notes

## Observability / Diagnostics
- Runtime signals: `reviewer_api.independence_warning`, `reviewer_api.independence_escalation`, `reviewer_api.independence_blocked` structured logs; 403 response with guard assertion metadata.
- Inspection surfaces: `review_decisions` table (`reviewer_independence_status`, `subject_author_id`, `decision_at`); reviewer API responses.
- Failure visibility: 403 response body contains guard assertion + invariant IDs; log event includes counts/percentage and reviewer/case IDs.
- Redaction constraints: do not log notes/dissent text or reviewer comments.

## Integration Closure
- Upstream surfaces consumed: `src/sps/api/routes/reviews.py`, `src/sps/db/models.py`, reviewer console entrypoint `/reviewer`.
- New wiring introduced in this slice: alembic migration for `subject_author_id`; rolling-quarter query in reviewer decision creation; docker-compose runbook.
- What remains before the milestone is truly usable end-to-end: nothing.

## Tasks
- [x] **T01: Implement rolling-quarter independence enforcement + migration + tests** `est:3h`
  - Why: This is the core governance requirement for S02 and must be enforced before decisions are written.
  - Files: `src/sps/api/routes/reviews.py`, `src/sps/db/models.py`, `src/sps/workflows/permit_case/contracts.py`, `alembic/versions/*`, `tests/m008_s02_reviewer_independence_thresholds_test.py`
  - Do: Add `subject_author_id` persistence on ReviewDecision rows (migration + ORM); compute 90-day UTC window metrics in `_check_reviewer_independence` or helper; set `reviewer_independence_status` to WARNING/ESCALATION_REQUIRED/BLOCKED per thresholds; emit structured warning/escalation/blocked logs; fail closed with guard assertion `INV-SPS-REV-001` when BLOCKED; extend tests to cover pass/warn/escalation/block with deterministic seeded history.
  - Verify: `. .venv/bin/activate && python -m pytest tests/m008_s02_reviewer_independence_thresholds_test.py -v -s`
  - Done when: tests pass and a new decision persists the computed independence status with proper enforcement semantics.
- [x] **T02: Add docker-compose runbook proving reviewer flow + thresholds** `est:2h`
  - Why: We need operational proof that the reviewer console + API + Postgres flow works end-to-end and thresholds enforce correctly.
  - Files: `scripts/verify_m008_s02.sh`, `scripts/verify_m007_s03.sh`
  - Do: Create a runbook that boots docker-compose, applies migrations, starts API/worker, seeds REVIEW_PENDING data + historical decisions to trigger warning/escalation/blocked thresholds, hits reviewer queue/evidence endpoints, submits decisions, and asserts DB state via `docker compose exec postgres psql`.
  - Verify: `bash scripts/verify_m008_s02.sh`
  - Done when: runbook exits 0 and shows expected queue/evidence + enforcement outcomes against live Postgres.

## Files Likely Touched
- `src/sps/api/routes/reviews.py`
- `src/sps/db/models.py`
- `alembic/versions/*`
- `tests/m008_s02_reviewer_independence_thresholds_test.py`
- `scripts/verify_m008_s02.sh`
