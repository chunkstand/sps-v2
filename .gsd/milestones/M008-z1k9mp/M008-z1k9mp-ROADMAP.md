# M008-z1k9mp: Phase 8 — reviewer UI + independence thresholds

**Vision:** Reviewer governance is usable end-to-end: a minimal reviewer console surfaces the queue, evidence, and decisions, and independence thresholds are enforced with clear warning/escalation signals.

## Success Criteria
- Reviewer can open the reviewer console, see REVIEW_PENDING cases, inspect evidence summaries, and submit ACCEPT/BLOCK/ACCEPT_WITH_DISSENT decisions through the real reviewer API.
- Rolling-quarter reviewer independence metrics are computed in UTC, persisted on ReviewDecision rows, and emit WARNING/ESCALATION_REQUIRED/BLOCKED signals per spec when thresholds are crossed.
- A live docker-compose runbook proves the UI + API + Postgres flow end-to-end, including threshold enforcement behavior.

## Key Risks / Unknowns
- Evidence aggregation requires stitching evidence IDs across multiple domain tables; risk of incomplete evidence summaries or N+1 API usage.
- No frontend stack exists yet; risk of overbuilding or introducing a complex toolchain for a minimal reviewer UX.
- Rolling-quarter threshold computation must be correct and fail-closed when data is missing; mistakes here weaken governance guarantees.

## Proof Strategy
- Evidence aggregation + reviewer UI viability → retire in S01 by proving a reviewer can browse queue items, open a case, and see aggregated evidence in the console via new API surfaces.
- Reviewer UI delivery stack choice → retire in S01 by shipping a FastAPI-served console without a frontend build toolchain.
- Rolling-quarter threshold enforcement correctness → retire in S02 by proving decision creation computes status + emits enforcement signals in tests and the runbook.

## Verification Classes
- Contract verification: pytest for reviewer queue/evidence endpoints + threshold computation policy tests.
- Integration verification: docker-compose runbook that exercises reviewer console + decision submission against live Postgres.
- Operational verification: runbook start/stop of API + worker (Temporal optional for review resume) and UI smoke validation.
- UAT / human verification: reviewer console UX smoke (manual click-through) for evidence visibility + decision capture.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slices are complete and demoable as written below.
- Reviewer console and reviewer API are wired together against real Postgres data.
- The reviewer console entrypoint exists and is exercised in a live runbook.
- Success criteria are re-checked against live behavior, not just tests.
- Final integrated acceptance scenarios (queue → evidence → decision with threshold enforcement) pass.

## Requirement Coverage
- Covers: R020, R021
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices
- [ ] **S01: Reviewer console MVP (queue + evidence + decision capture)** `risk:high` `depends:[]`
  > After this: a reviewer can open the console, view REVIEW_PENDING cases, inspect aggregated evidence summaries, and submit decisions through the real API (threshold enforcement still minimal).
- [ ] **S02: Independence thresholds + end-to-end runbook** `risk:medium` `depends:[S01]`
  > After this: decision submission computes rolling-quarter independence status with warning/escalation signals, and the full reviewer flow is proven via a live docker-compose runbook.

## Boundary Map
### S01 → S02
Produces:
- Reviewer queue endpoint (e.g., `GET /api/v1/reviews/queue`) returning queue items with case + project summary fields.
- Evidence summary endpoint (e.g., `GET /api/v1/reviews/cases/{case_id}/evidence-summary`) aggregating evidence IDs + metadata references.
- Reviewer console entrypoint (e.g., `GET /reviewer`) served by FastAPI with minimal JS calling the reviewer API.
- UI contract for decision submission payloads using existing `POST /api/v1/reviews/decisions`.

Consumes:
- None (first slice).

### S02 → Final Integration
Produces:
- Rolling-quarter independence computation wired into decision creation with persisted `reviewer_independence_status` and enforcement metadata in responses/logs.
- Runbook script proving queue → evidence → decision with threshold enforcement against docker-compose Postgres.

Consumes:
- S01 reviewer console + queue/evidence APIs.
