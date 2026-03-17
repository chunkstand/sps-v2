# M013-n6p1tg: Phase 13 — admin policy/config governance

**Vision:** Admin policy/config changes (portal support metadata, source rules, incentive programs) are governed through intent → review → apply with durable audit trails and fail-closed enforcement.

## Success Criteria
- Admins can create an intent for a portal support metadata change, reviewers can approve it, and the apply endpoint updates the authoritative config only with an approved review.
- Admin changes for source rules and incentive programs are applied only through the governed pathway, with direct mutation paths denied.
- Every admin intent, review decision, and apply action emits a durable audit event linked to the change artifact.
- A live docker-compose runbook proves intent → review → apply → audit trail for all three admin change types.

## Key Risks / Unknowns
- Reviewer approval model must avoid the `ReviewDecision.case_id` constraint while still aligning with reviewer authority semantics.
- Fixture-backed config data must be migrated to an authoritative mutable store without silent drift or bypass paths.

## Proof Strategy
- Reviewer approval model constraint → retire in S01 by proving admin-specific review artifacts can be created/approved and queried without a case.
- Fixture-backed config drift risk → retire in S02 by proving governed apply endpoints are the only mutation path for all three change types in a live runbook.

## Verification Classes
- Contract verification: pytest admin intent/review/apply API tests + audit event assertions.
- Integration verification: docker-compose runbook exercising admin intent → review → apply → audit for all change types.
- Operational verification: runbook start/stop with real API + Postgres interactions.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slices below are complete and merged.
- Admin intent, review, and apply flows are wired into the API with RBAC enforcement and audit events.
- Governed admin apply endpoints are the only mutation path for portal support metadata, source rules, and incentive programs.
- Success criteria are re-checked against live docker-compose behavior.
- Final integrated acceptance scenarios (intent → review → apply → audit) pass for all three admin change types.

## Requirement Coverage
- Covers: R035
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices
- [ ] **S01: Admin intent/review/apply for portal support metadata** `risk:high` `depends:[]`
  > After this: An admin can create a portal support change intent in the admin console/API, a reviewer can approve it, and the governed apply endpoint updates portal support metadata with audit events (proved by integration tests).
- [ ] **S02: Governed admin changes for source rules + incentive programs with live runbook** `risk:medium` `depends:[S01]`
  > After this: The same governed workflow applies to source rules and incentive programs, and a docker-compose runbook proves intent → review → apply → audit across all three change types.

## Boundary Map

### S01 → S02
Produces:
- Admin change intent + review + apply schemas for portal support metadata (DB models + API contracts).
- Governed apply endpoint + audit event types for portal support metadata changes.
- Admin console surface for creating intents and inspecting approvals.

Consumes:
- RBAC role checks and audit event sink (existing).
