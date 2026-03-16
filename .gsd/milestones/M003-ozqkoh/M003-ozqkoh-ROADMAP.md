# M003-ozqkoh Roadmap

**Milestone:** Phase 3 — reviewer service + independence/dissent/contradiction governance  
**Status:** queued  
**Risk profile:** High — changes authority boundary between HTTP API and Temporal orchestration  
**Proof strategy:** End-to-end integration first (HTTP → Postgres → Temporal signal → workflow resume), then layer governance policies on top

## Decomposition Rationale

M003 flips the ReviewDecision authority boundary from "workflow writes decisions" to "reviewer API is sole writer." The highest risk is the operational contract change: if signal delivery fails or the boundary is misconfigured, we get "review recorded but workflow stuck forever" scenarios.

The research recommends proving the HTTP → Postgres → Temporal signal → workflow resume path first (S01), then adding governance layers (independence/contradictions/dissent in S02–S04). This front-loads the integration risk and establishes a working reviewer API before tightening policy enforcement.

All four Active requirements (R006–R009) map to slices; no orphans.

## Slices

### S01: Reviewer API authority boundary ✓ primary integration proof
- **Risk:** High — operational contract change; signal delivery critical path
- **Depends on:** M002 (guarded transitions + Temporal harness)
- **Demo:** Start local stack, start a PermitCaseWorkflow via CLI, observe denial and `REVIEW_PENDING` state. Record a ReviewDecision via `POST /api/v1/reviews/decisions` with idempotency key, observe workflow resume and transition to `APPROVED_FOR_SUBMISSION`. Query Postgres and confirm exactly one `review_decisions` row and one `CASE_STATE_CHANGED` ledger event. Retry the POST with same idempotency key and identical payload → 200 (existing). Retry with conflicting payload → 409.
- **Proof:** Temporal+Postgres integration test proving HTTP reviewer API writes ReviewDecision, signals workflow, workflow resumes and applies protected transition. Idempotency conflict (409) test. Post-slice verification: `bash scripts/verify_m003_s01.sh` (runbook analog to M002/S03).
- **Establishes:** Reviewer API HTTP surface, ReviewDecision sole-writer authority boundary, workflow signal delivery pattern, idempotency semantics at API boundary
- **Requirement coverage:** R006 (primary)

### S02: Reviewer independence policy guard
- **Risk:** Medium — independence semantics underspecified (no author model yet); must fail closed
- **Depends on:** S01 (reviewer API writes ReviewDecision)
- **Demo:** Attempt to record a ReviewDecision for a high-risk surface where `reviewer_id == subject_author_id` (self-approval) → API returns 403 with `guard_assertion_id=INV-SPS-REV-001` and normalized invariant `INV-008`. Record a valid decision with distinct reviewer/author → succeeds.
- **Proof:** Integration test proving self-approval denial on high-risk surfaces + stable guard/invariant identifiers in denial payload.
- **Establishes:** Fail-closed reviewer independence checks, stable denial identifiers for independence violations
- **Requirement coverage:** R007 (primary)

### S03: Contradiction artifacts + advancement blocking
- **Risk:** Medium — guard must block deterministically; contradiction create/resolve must be idempotent
- **Depends on:** S01 (guarded transitions proven end-to-end)
- **Demo:** Create a blocking contradiction artifact for a case in `REVIEW_PENDING`. Attempt protected transition → denied with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`. Resolve the contradiction via API. Re-attempt transition → succeeds.
- **Proof:** Integration test proving contradiction blocking in `apply_state_transition` guard + manual create/resolve API endpoints + stable denial identifiers.
- **Establishes:** Contradiction artifact CRUD API, guarded advancement blocking on unresolved contradictions, CTL-14A denial audit event type
- **Requirement coverage:** R008 (primary)

### S04: Dissent artifacts
- **Risk:** Low — record-only surface; no blocking behavior
- **Depends on:** S01 (ReviewDecision persistence proven)
- **Demo:** Record an `ACCEPT_WITH_DISSENT` ReviewDecision via API. Query Postgres and observe a persisted `dissent_artifacts` row linked to the `ReviewDecision.decision_id`. Query dissent via API and confirm artifact is returned with resolution state.
- **Proof:** Integration test proving dissent persistence for ACCEPT_WITH_DISSENT decisions + API query endpoint.
- **Establishes:** Dissent artifact persistence + query API, audit trail for accept-with-dissent outcomes
- **Requirement coverage:** R009 (primary)

## Milestone Definition of Done

When all slices are complete:

- A PermitCaseWorkflow can be started, denied at the protected transition, then unblocked by a ReviewDecision recorded via HTTP API (not CLI signal injection), and the workflow resumes and succeeds.
- Idempotency conflicts (same key, different payload) return 409 with stable error shape.
- Self-approval on high-risk surfaces is denied with stable `guard_assertion_id=INV-SPS-REV-001` + `INV-008`.
- Unresolved blocking contradictions prevent advancement with stable `guard_assertion_id=INV-SPS-CONTRA-001` + `INV-003`; resolving them allows advancement.
- Accept-with-dissent decisions create durable dissent artifacts linked to the originating ReviewDecision, queryable via API.
- All of the above proven against real docker-compose Temporal + Postgres (not only unit tests).

## Boundary Map

This milestone crosses the following runtime boundaries:

- **HTTP API (FastAPI)** — reviewer endpoints under `/api/v1/reviews/...`
- **Postgres** — authoritative ReviewDecision/contradiction/dissent writes + guarded state transitions
- **Temporal** — signal delivery to waiting workflows; workflow resume + re-attempt protected transition
- **Integration surface** — S01 proves the assembled HTTP → Postgres → Temporal signal → workflow path works end-to-end in docker-compose

External dependencies:
- Postgres (docker-compose service `postgres`)
- Temporal (docker-compose service `temporal`)
- MinIO (optional; not exercised in M003 core paths)

## Requirement Coverage

| Requirement | Status before | Primary owner | Supporting | Status after | Proof |
|-------------|---------------|---------------|------------|--------------|-------|
| R006 | active | S01 | none | validated | Temporal+Postgres integration test + runbook |
| R007 | active | S02 | none | validated | independence denial integration test |
| R008 | active | S03 | none | validated | contradiction blocking integration test |
| R009 | active | S04 | none | validated | dissent persistence integration test |

### Coverage Summary
- Active requirements at planning: 4
- Mapped to slices: 4
- Unmapped active requirements: 0
- Orphaned slices (no requirement justification): 0

All Active requirements have a primary owner and a proof strategy.
