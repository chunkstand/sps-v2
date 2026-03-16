# M005-j3c8qk: Phase 5 — compliance and incentives workers

**Vision:** Enable fixture-backed compliance evaluation and incentive assessment that persist authoritative artifacts, advance PermitCaseWorkflow through COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE, and prove the live end-to-end path against docker-compose Postgres + Temporal.

## Success Criteria
- A workflow run persists a ComplianceEvaluation with rule-by-rule results, blockers/warnings, and provenance, and it is queryable via the case API.
- The same workflow run persists an IncentiveAssessment with eligibility results + provenance and is queryable via the case API.
- A docker-compose runbook proves the workflow reaches INCENTIVES_COMPLETE with both artifacts present in Postgres and ledgered transitions.

## Key Risks / Unknowns
- Deterministic evaluation: rule evaluation must stay deterministic for Temporal replay safety.
- Fixture completeness/provenance: rule fixtures must be traceable and stable to avoid idempotent conflicts and audit gaps.
- Guarded progression: missing or stale evaluation artifacts could cause workflow advancement to stall unexpectedly.

## Proof Strategy
- Deterministic evaluation → retire in S01 by persisting ComplianceEvaluation via activity-only rule evaluation and proving replay-safe behavior in integration tests.
- Fixture completeness/provenance → retire in S01 by loading spec-sourced phase5 fixtures with stable IDs and persisting provenance JSONB fields.
- Guarded progression → retire in S02 by driving the workflow through COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE with guard checks + persisted IncentiveAssessment.

## Verification Classes
- Contract verification: pytest integration tests for compliance/incentive activities + API read endpoints; fixture artifact shape checks.
- Integration verification: docker-compose runbook exercising API + Temporal worker + Postgres for both artifacts.
- Operational verification: runbook scripts that restart worker and assert ledger + artifact persistence.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- S01–S03 are complete and merged.
- PermitCaseWorkflow reaches COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE via real activities (not workflow-side evaluation).
- The real entrypoint (`uvicorn` + worker) is exercised in docker-compose and both artifacts are present in Postgres.
- Success criteria are re-checked against the live runbook output.
- Final integrated acceptance scenarios in the runbook pass with no manual DB edits.

## Requirement Coverage
- Covers: R013, R014
- Partially covers: none
- Leaves for later: R015, R016, R017, R018, R019, R020, R021, R022, R023, R024, R025, R026, R027, R028, R029, R031, R032, R033, R034, R035
- Orphan risks: none

## Slices
- [x] **S01: Compliance evaluation artifacts + workflow advance** `risk:high` `depends:[]`
  > After this: A case can advance to COMPLIANCE_COMPLETE with a persisted ComplianceEvaluation (rule results + provenance) retrievable via the case API, proven by integration tests (fixture-backed).
- [x] **S02: Incentive assessment artifacts + workflow advance** `risk:medium` `depends:[S01]`
  > After this: The workflow advances to INCENTIVES_COMPLETE with a persisted IncentiveAssessment (eligibility + provenance) retrievable via the case API, proven by integration tests.
- [ ] **S03: End-to-end docker-compose proof for compliance + incentives** `risk:low` `depends:[S02]`
  > After this: The operator runbook proves the live API + Temporal worker + Postgres path reaches INCENTIVES_COMPLETE with both artifacts present and ledgered.

## Boundary Map
### S01 → S02
Produces:
- ComplianceEvaluation table/model + Alembic migration with JSONB provenance/evidence fields.
- Compliance fixtures + deterministic evaluator + activity persistence contract.
- `GET /api/v1/cases/{case_id}/compliance` read surface returning rule results + provenance.
- Workflow transition to COMPLIANCE_COMPLETE guarded by compliance freshness assertions.

Consumes:
- Phase 4 Project/Jurisdiction/RequirementSet artifacts and fixture override pattern.

### S02 → S03
Produces:
- IncentiveAssessment table/model + migration with provenance fields.
- Incentive fixtures + deterministic evaluator + activity persistence contract.
- `GET /api/v1/cases/{case_id}/incentives` read surface returning program eligibility + provenance.
- Workflow transition to INCENTIVES_COMPLETE guarded by incentive freshness assertions.

Consumes:
- ComplianceEvaluation artifacts and COMPLIANCE_COMPLETE workflow state from S01.

### S01 → S03
Produces:
- Compliance activity + API endpoints used by the end-to-end runbook and DB assertions.

Consumes:
- None (first slice).
