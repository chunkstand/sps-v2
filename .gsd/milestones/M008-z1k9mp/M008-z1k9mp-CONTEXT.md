# M008-z1k9mp: Phase 8 — reviewer UI + independence thresholds — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement reviewer-facing UI surfaces and independence threshold enforcement. This milestone delivers a minimal web UI for reviewer queue, evidence inspection, and decision capture, plus rolling-quarter reviewer independence thresholds (per spec) with enforcement/escalation signals. It builds on the existing reviewer API and the domain artifacts produced in M004–M007.

## Why This Milestone

The system currently exposes reviewer APIs but no reviewer UX, and only enforces self-approval denial. Spec requires reviewer independence thresholds and auditable review workflows. This milestone makes reviewer governance usable and enforces the independence metrics required for Tier 3 compliance.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open a reviewer web UI to view queued cases, inspect evidence/artifacts, and submit decisions.
- Observe threshold enforcement when reviewer independence limits are breached (warning/escalation per spec).

### Entry point / environment

- Entry point: reviewer web UI + existing `POST /api/v1/reviews/decisions`
- Environment: local dev (web + API + docker compose)
- Live dependencies involved: Postgres, Temporal (optional for workflow resume)

## Completion Class

- Contract complete means: UI captures decisions using existing API contracts and independence threshold checks emit expected enforcement signals.
- Integration complete means: reviewer UI flows operate end-to-end against real Postgres-backed data.
- Operational complete means: tests + runbook prove reviewer queue, decision capture, and threshold enforcement behavior.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Reviewer UI shows cases and artifacts, and can submit ACCEPT/BLOCK/ACCEPT_WITH_DISSENT decisions.
- Independence thresholds are evaluated over rolling-quarter history and enforce warnings/escalation as specified.
- The above is proven against live docker-compose Postgres (and Temporal for workflow resume when applicable).

## Risks and Unknowns

- UX scope creep — keep UI minimal and focused on queue + evidence + decision capture.
- Threshold data completeness — historical review data may be sparse in dev fixtures.

## Existing Codebase / Prior Art

- `src/sps/api/routes/reviews.py` — reviewer decision API and independence guard.
- `src/sps/api/routes/evidence.py` — evidence retrieval surface for UI.
- `specs/sps/build-approved/spec.md` — reviewer independence thresholds and UI requirements.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R020 — Reviewer UI queue/evidence view/decision capture (E-001).
- R021 — Reviewer independence thresholds enforced (E-002).

## Scope

### In Scope

- Minimal reviewer web UI (queue, evidence view, decision capture).
- Rolling-quarter independence threshold computation and enforcement signals.
- Integration tests + operator runbook proving reviewer flow and threshold enforcement.

### Out of Scope / Non-Goals

- Full reviewer analytics dashboards or bulk review tooling.
- Release gating changes beyond threshold enforcement signals.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Reviewer decisions remain authoritative only via reviewer API.
- Threshold enforcement must not allow self-approval or fail-open bypasses.

## Integration Points

- Postgres — review decision history and threshold computation.
- Reviewer API — decision persistence and workflow signaling.
- Evidence registry — artifact retrieval for UI.

## Open Questions

- UI framework choice (if not already established) — decide during planning.
