---
id: M008-z1k9mp
provides:
  - reviewer console MVP (queue + evidence + decision capture)
  - rolling-quarter reviewer independence enforcement with subject_author_id persistence
  - docker-compose reviewer runbook covering queue → evidence → decisions with threshold enforcement assertions
key_decisions:
  - Evidence summary responses include review decision summaries with reviewer independence status.
  - Jinja2 template entrypoint for minimal reviewer consoles (no frontend toolchain).
  - repeated pair rate uses (pair_total_reviews - 1) / total_reviews to avoid first-review blocking
  - reset review_decisions between threshold scenarios to keep rolling-quarter rates deterministic
patterns_established:
  - Union-based evidence ID aggregation with a single metadata fetch per case.
  - Postgres-backed reviewer independence threshold tests seed history via ReviewDecision rows and real API calls
  - runbook seeds reviewer history with pg_exec + per-scenario truncation and asserts API + Postgres outcomes
observability_surfaces:
  - reviewer_api.queue_fetched structured log event
  - reviewer_api.evidence_summary structured log event
  - reviewer_api.independence_warning / reviewer_api.independence_escalation / reviewer_api.independence_blocked logs
  - GET /api/v1/reviews/queue
  - GET /api/v1/reviews/cases/{case_id}/evidence-summary
  - GET /reviewer (UI error banner for API failures)
  - review_decisions.subject_author_id + reviewer_independence_status
requirement_outcomes:
  - id: R020
    from_status: active
    to_status: validated
    proof: integration tests passed + S02 docker-compose runbook exercising end-to-end API flows
  - id: R021
    from_status: active
    to_status: validated
    proof: pytest tests/m008_s02_reviewer_independence_thresholds_test.py + scripts/verify_m008_s02.sh runbook
duration: 6.6h
verification_result: passed
completed_at: 2026-03-16
---

# M008-z1k9mp: Phase 8 — reviewer UI + independence thresholds

**Reviewer queue/evidence APIs, a FastAPI-served reviewer console, and rolling-quarter independence threshold enforcement are now shipped and proven via a live docker-compose runbook.**

## What Happened

We shipped the core surfaces for reviewer governance and independence enforcement. In S01, we delivered new REST endpoints for the reviewer queue and evidence summaries, which aggregate evidence metadata across domain tables and include prior decision status. We then wired these endpoints into a minimal Jinja2-served `/reviewer` console, allowing a reviewer to browse pending cases, inspect evidence, and submit decisions directly through the reviewer API without needing a separate frontend build toolchain.

In S02, we expanded the reviewer API to enforce 90-day rolling-window independence thresholds. We added `subject_author_id` to the `ReviewDecision` schema and implemented calculations that track the pair repetition rate. Depending on this rate, the API now transparently enforces warning (>25%), escalation (>35%), and block (>50%) thresholds, durably persisting these states and emitting the specified structured logs. When blocked, the system fails closed and returns an `INV-SPS-REV-001` guard assertion. 

The entire end-to-end flow is validated by a live docker-compose runbook that seeds historical decision records, submits reviews representing every threshold condition, and verifies the API and Postgres outcomes.

## Cross-Slice Verification

- **Reviewer can open the reviewer console, see REVIEW_PENDING cases, inspect evidence summaries, and submit decisions:** Verified via `tests/m008_s01_reviewer_console_page_test.py` and manually via the `/reviewer` UI route in the live runbook scenario.
- **Rolling-quarter reviewer independence metrics are computed in UTC, persisted on ReviewDecision rows, and emit signals per spec:** Verified via `tests/m008_s02_reviewer_independence_thresholds_test.py` and Postgres assertions on `reviewer_independence_status` and `subject_author_id`. 
- **A live docker-compose runbook proves the UI + API + Postgres flow end-to-end:** `scripts/verify_m008_s02.sh` successfully boots the local stack, seeds pairings, executes HTTP requests reflecting the console's interactions, and verifies threshold escalations directly via database queries.

## Requirement Changes

- R020: active → validated — proved via integration tests and S02 docker-compose runbook exercising end-to-end UI/API flows.
- R021: active → validated — proved via pytest `tests/m008_s02_reviewer_independence_thresholds_test.py` and the `scripts/verify_m008_s02.sh` runbook enforcing warnings, escalations, and blocks.

## Forward Intelligence

### What the next milestone should know
- Evidence summary responses already include review decision summaries (with independence status), so the UI can render decision context without extra calls.
- The rolling-quarter pair rate calculation uses `(pair_total_reviews - 1) / total_reviews`. This prevents a first-time review pair (1 out of 1 total) from immediately tripping the 100% block threshold.

### What's fragile
- Evidence aggregation depends on the union of multiple case-linked tables; future schema changes need to update the aggregation list to avoid missing artifacts.
- The threshold calculation runs a `COUNT(*)` query across the last 90 days per decision submission. It's performant now but lacks an index on `(reviewer_id, subject_author_id, decision_at)`.

### Authoritative diagnostics
- `/api/v1/reviews/queue` + `reviewer_api.queue_fetched` log events are the quickest signal for queue data correctness.
- The structured logs (`reviewer_api.independence_blocked`, etc.) and the 403 `INV-SPS-REV-001` response body are the authoritative signals when debugging why a reviewer was denied.
- `review_decisions.reviewer_independence_status` and `review_decisions.subject_author_id` in Postgres are the source of truth for historical enforcement.

### What assumptions changed
- We originally assumed a frontend build toolchain might be needed; Jinja2 + vanilla JS proved sufficient for the MVP console.
- We thought Temporal might be needed to enforce independence across concurrent workflows, but handling it synchronously in the FastAPI Postgres transaction proved much simpler and provided immediate fail-closed feedback to the reviewer.

## Files Created/Modified

- `src/sps/api/contracts/reviews.py` — reviewer queue/evidence response contracts.
- `src/sps/api/routes/reviews.py` — queue/evidence endpoints + independence thresholds computation and logs.
- `src/sps/api/routes/reviewer_console.py` — reviewer console router.
- `src/sps/api/templates/reviewer_console.html` — console UI shell + inline JS wiring.
- `src/sps/api/main.py` — mounted reviewer console router.
- `src/sps/db/models.py` — Added nullable `subject_author_id` to ReviewDecision.
- `alembic/versions/f4c2b1a9d0e3_review_decisions_subject_author_id.py` — Migration for subject_author_id column.
- `tests/m008_s01_reviewer_queue_evidence_test.py` — integration tests for queue/evidence.
- `tests/m008_s01_reviewer_console_page_test.py` — HTML contract test for `/reviewer`.
- `tests/m008_s02_reviewer_independence_thresholds_test.py` — Integration coverage for PASS/WARNING/ESCALATION_REQUIRED/BLOCKED.
- `scripts/verify_m008_s02.sh` — End-to-end reviewer runbook with threshold seeding, API calls, and Postgres assertions.
- `pyproject.toml` — added Jinja2 dependency.
