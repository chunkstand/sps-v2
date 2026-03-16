# S02 — Research

**Date:** 2026-03-16

## Summary

S02 owns R021 (rolling-quarter reviewer independence thresholds) and finishes R020 validation by adding a live docker-compose runbook that proves the reviewer UI → API → Postgres flow end-to-end. The current reviewer API only enforces self-approval (reviewer_id == subject_author_id) before any DB work, and ReviewDecision rows persist `reviewer_independence_status` but there is no rolling-quarter computation. The schema also does not store `subject_author_id`, so author–reviewer pair concentration cannot be computed from historical rows without adding new data or another joinable source of author identity.

The spec’s thresholds require a 90-day UTC window and denominator-based repeated-pair frequency, with warning/escalation/blocker statuses; this implies new query logic, deterministic handling of missing data, and explicit structured log signals when thresholds cross. There is no runbook script for the reviewer console yet; existing runbooks (e.g., M007) establish a pattern for docker-compose startup, migrations, API + worker launch, fixture cleanup, and API assertions.

## Recommendation

Add persisted author identity for reviewer independence metrics (likely a `subject_author_id` column on `review_decisions` with an Alembic migration) and compute rolling-quarter metrics inside `create_review_decision` prior to insert. Reuse `_utcnow()` for UTC window boundaries and enforce fail-closed behavior: if the rolling window or denominator cannot be computed, set status to `BLOCKED` and return a 403 with `INV-SPS-REV-001`. Emit structured logs for `reviewer_api.independence_warning`, `reviewer_api.independence_escalation`, and `reviewer_api.independence_blocked` with non-sensitive counts/percentages only. Persist the computed `reviewer_independence_status` on the ReviewDecision row so evidence summaries and downstream dashboards can use it.

For the runbook, follow the `scripts/verify_m007_s03.sh` pattern: ensure docker compose is up, apply migrations, start API + worker, seed a REVIEW_PENDING case (intake + workflow), call queue/evidence endpoints, post a decision, and assert DB state. Include a deterministic pre-seed of review_decisions to trigger WARNING/ESCALATION_REQUIRED/BLOCKED thresholds via SQL inserts so the runbook proves enforcement behavior against live Postgres.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Reviewer auth gating | `require_reviewer_api_key` in `src/sps/api/routes/reviews.py` | Keeps reviewer surfaces consistently keyed and avoids duplicating credential checks. |
| Guard invariant mapping | `get_normalized_business_invariants` in `sps.guards.guard_assertions` | Ensures denials carry stable guard/invariant IDs per spec. |
| UTC timestamps | `_utcnow()` in `src/sps/api/routes/reviews.py` | Keeps rolling-window computations UTC-consistent with current decision timestamps. |
| Runbook orchestration | `scripts/verify_m007_s03.sh` | Established docker-compose + API/worker boot + Postgres assertion patterns. |

## Existing Code and Patterns

- `src/sps/api/routes/reviews.py` — `_check_reviewer_independence()` runs before idempotency; `create_review_decision()` persists `reviewer_independence_status="PASS"` and logs structured events.
- `src/sps/db/models.py` — `ReviewDecision` schema lacks `subject_author_id`, which is required for author–reviewer pair calculations.
- `src/sps/workflows/permit_case/contracts.py` — `ReviewerIndependenceStatus` enum defines PASS/WARNING/ESCALATION_REQUIRED/BLOCKED for persistence.
- `scripts/verify_m007_s03.sh` — runbook template for docker-compose + API/worker + DB assertions.
- `src/sps/api/templates/reviewer_console.html` — reviewer console UI expects `X-Reviewer-Api-Key` header and fetches queue/evidence endpoints directly.

## Constraints

- Rolling-quarter metrics must be computed using UTC (`decision_at`) and a 90-day window; fail-closed on missing data or denominator == 0.
- Reviewer API surfaces remain dev-key gated; the runbook must supply `X-Reviewer-Api-Key` for all reviewer endpoints.
- There is no high-risk surface classification in request payloads today; all review decisions are implicitly high-risk unless a new field is introduced.

## Common Pitfalls

- **Fail-open metrics** — If rolling window data is missing or denominator is zero, return a denial (403) and mark status `BLOCKED` rather than defaulting to PASS.
- **Missing author identity** — Rolling-quarter repeated-pair calculations require persisted author IDs; avoid computing from transient request data only.
- **Leaking reviewer text** — Do not log `notes` or dissent text; follow existing `scope_len` patterns in structured logs.

## Open Risks

- Adding `subject_author_id` to `review_decisions` requires a migration and careful backfill strategy for existing rows used in tests.
- Sparse local fixtures may not cover warning/escalation thresholds; runbook/test data must deterministically seed historical decisions.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available (not installed) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (not installed) |
| Docker Compose | manutej/luxor-claude-marketplace@docker-compose-orchestration | available (not installed) |

## Sources

- Reviewer independence thresholds (source: [spec.md](specs/sps/build-approved/spec.md))
- Reviewer decision endpoint + independence guard placement (source: [reviews.py](src/sps/api/routes/reviews.py))
- ReviewDecision schema (source: [models.py](src/sps/db/models.py))
- Reviewer independence status enum (source: [contracts.py](src/sps/workflows/permit_case/contracts.py))
- Runbook pattern (source: [verify_m007_s03.sh](scripts/verify_m007_s03.sh))
