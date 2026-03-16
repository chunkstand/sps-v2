# M003-ozqkoh Roadmap

**Milestone:** Phase 3 — reviewer service + independence/dissent/contradiction governance  
**Status:** active  
**Risk profile:** High — changes authority boundary between HTTP API and Temporal orchestration  
**Proof strategy:** End-to-end integration first (HTTP → Postgres → Temporal signal → workflow resume), then layer governance policies on top

## Decomposition Rationale

M003 flips the ReviewDecision authority boundary from "workflow writes decisions" to "reviewer API is sole writer." The highest risk is the operational contract change: if signal delivery fails or the boundary is misconfigured, we get "review recorded but workflow stuck forever" scenarios.

The research recommends proving the HTTP → Postgres → Temporal signal → workflow resume path first (S01), then adding governance layers (independence/contradictions/dissent in S02–S04). This front-loads the integration risk and establishes a working reviewer API before tightening policy enforcement.

All four Active requirements (R006–R009) map to slices; no orphans.

## Slices

- [x] **S01: Reviewer API authority boundary** `risk:high` `depends:[]`
  > After this: A PermitCaseWorkflow in REVIEW_PENDING is unblocked by POST /api/v1/reviews/decisions against a live docker-compose run; workflow resumes to APPROVED_FOR_SUBMISSION; idempotency conflict returns 409 — proven by integration test and verify_m003_s01.sh runbook.

- [ ] **S02: Reviewer independence policy guard** `risk:medium` `depends:[S01]`
  > After this: Self-approval on a high-risk surface returns 403 with guard_assertion_id=INV-SPS-REV-001; valid distinct-reviewer decision succeeds — proven by integration test.

- [ ] **S03: Contradiction artifacts + advancement blocking** `risk:medium` `depends:[S01]`
  > After this: A blocking contradiction prevents protected transition with stable denial identifiers; resolving it allows advancement — proven by integration test against real docker-compose.

- [ ] **S04: Dissent artifacts** `risk:low` `depends:[S01]`
  > After this: ACCEPT_WITH_DISSENT decisions persist a dissent_artifacts row linked to the ReviewDecision, queryable via API — proven by integration test.

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
