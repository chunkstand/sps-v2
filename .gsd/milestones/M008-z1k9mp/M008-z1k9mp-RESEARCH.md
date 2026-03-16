# M008-z1k9mp — Research
**Date:** 2026-03-16

## Summary
Reviewer UX is currently absent: there is no frontend stack, no reviewer queue endpoint, and no case listing route. The reviewer authority boundary exists at `POST /api/v1/reviews/decisions`, evidence metadata/download endpoints exist, and contradictions/dissent endpoints are reviewer-key gated. For a minimal reviewer UI, the API will need a queue/list surface that exposes `PermitCase` rows in `REVIEW_PENDING` (and probably `Project` metadata), plus an evidence aggregation surface that can stitch together evidence IDs from jurisdiction/requirements/compliance/incentives/package/manifest/submission artifacts. The UI can be minimal, but it needs a stable API to avoid N+1 fetches and ensure evidence + contradictions are visible per spec.

Reviewer independence thresholds are only enforced for self-approval today. The guard assertion `INV-SPS-REV-001` explicitly includes threshold-breaching repeated author-reviewer pairs, but no rolling-quarter computation exists. The new logic should compute rolling-quarter pair repetition rates from `review_decisions` (90-day window) and translate the result into `reviewer_independence_status` values (`PASS`, `WARNING`, `ESCALATION_REQUIRED`, `BLOCKED`) with explicit structured logs and response payloads. The spec’s metrics (<=25% OK, >25% warning, >35% release escalation) imply enforcement signals, not necessarily hard blocks, but the API must fail closed if it cannot compute the threshold.

Primary recommendation: add API surfaces first (queue + evidence summary + threshold computation with response/log fields) and prove them with Postgres-backed tests before building UI. This keeps the UI thin and avoids duplicating query logic in the browser.

## Recommendation
Implement reviewer queue + evidence aggregation endpoints in the FastAPI app first, using SQLAlchemy queries against `permit_cases`, `projects`, and the domain artifact tables that already store `evidence_ids`. Then implement rolling-quarter independence threshold computation as part of `create_review_decision` (pre-DB insert), writing the resulting `reviewer_independence_status` to the ReviewDecision row and emitting structured logs when WARNING/ESCALATION_REQUIRED/BLOCKED occurs. Once the API is stable, build a minimal UI (server-rendered or small static app) that calls the queue and evidence summary endpoints and posts to `/api/v1/reviews/decisions`.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Reviewer auth gating | `require_reviewer_api_key` in `src/sps/api/routes/reviews.py` | Ensures reviewer-only surfaces reuse the same dev-key auth boundary and avoids duplicated logic. |
| Guard invariant mapping | `sps.guards.guard_assertions.get_normalized_business_invariants` | Keeps denial responses consistent with invariant registry and spec-linked guard IDs. |
| Evidence metadata + presign | `src/sps/api/routes/evidence.py` | Evidence registry already defines stable IDs and download URLs; reuse instead of new storage logic. |
| Temporal signal delivery | `_send_review_signal` in `src/sps/api/routes/reviews.py` | Preserves authority boundary: Postgres write is authoritative, signal is best-effort. |

## Existing Code and Patterns
- `src/sps/api/routes/reviews.py` — reviewer decision API, idempotency, independence guard, and Temporal signal pattern; reuse for threshold enforcement and decision status updates.
- `src/sps/db/models.py` — `PermitCase`, `ReviewDecision`, and evidence-bearing domain tables; queue and aggregation queries should use these models.
- `src/sps/api/routes/evidence.py` — evidence metadata + presigned download URL; UI should rely on these endpoints rather than direct S3 access.
- `src/sps/workflows/permit_case/contracts.py` — `ReviewerIndependenceStatus` enum and review decision contracts; use for status values.
- `invariants/sps/guard-assertions.yaml` — `INV-SPS-REV-001` includes threshold-breach semantics; use for stable guard IDs in denial/warning logs.

## Constraints
- There is no existing frontend stack or `package.json`; UI must be added from scratch or served via FastAPI.
- No reviewer queue or case list endpoint exists; current API only supports per-case artifact reads.
- Reviewer endpoints are dev-key gated; no RBAC/auth layer exists yet (Phase 10 scope).
- Evidence IDs are distributed across multiple domain tables; evidence aggregation will require explicit joins/queries.

## Common Pitfalls
- **Leaking reviewer text in logs** — dissent scope/rationale must never be logged; follow existing `scope_len` pattern.
- **Fail-open threshold logic** — if rolling-quarter metrics cannot be computed (missing data/window), the guard should fail closed or mark status as `BLOCKED` with explicit error detail.
- **N+1 evidence fetches in UI** — add aggregation endpoints so the UI doesn’t call evidence metadata for each ID serially.
- **Time window skew** — rolling-quarter should be computed in UTC using `decision_at` to avoid timezone drift.

## Open Risks
- Sparse local fixture data may not cover rolling-quarter thresholds; tests will need deterministic seed data.
- Spec requires review surfaces to show producer/version/confidence/citations/contradictions, but those fields are not consistently persisted across domain artifacts yet.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available (not installed) |
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (not installed) |
| SQLAlchemy/Alembic | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (not installed) |

## Sources
- Reviewer independence thresholds + reviewer story acceptance criteria (source: [spec.md](specs/sps/build-approved/spec.md))
- Reviewer decision API + independence guard + signal delivery (source: [reviews.py](src/sps/api/routes/reviews.py))
- Evidence registry endpoints (source: [evidence.py](src/sps/api/routes/evidence.py))
- ReviewDecision and PermitCase models (source: [models.py](src/sps/db/models.py))
- Guard assertion for independence thresholds (source: [guard-assertions.yaml](invariants/sps/guard-assertions.yaml))
