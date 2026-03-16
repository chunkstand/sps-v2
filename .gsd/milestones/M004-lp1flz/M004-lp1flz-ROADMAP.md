# M004-lp1flz: Phase 4 — intake, jurisdiction, and requirements workers

**Vision:** Turn spec-derived intake into a durable Project, resolve jurisdiction + requirements with provenance, and advance PermitCaseWorkflow through INTAKE/JURISDICTION/RESEARCH states using fixture-backed authoritative data.

## Success Criteria
- Intake payloads that conform to the spec-derived contract create a PermitCase + Project and the workflow reaches INTAKE_COMPLETE.
- JurisdictionResolution and RequirementSet artifacts with provenance are persisted for a case and are inspectable via API/DB.
- A docker-compose-backed workflow run reaches RESEARCH_COMPLETE using the real API + Temporal worker (no mocks).

## Key Risks / Unknowns
- Workflow wiring risk — new activities + state transitions must remain deterministic and guard-mediated.
- Fixture fidelity risk — jurisdiction/requirements fixtures may not match spec/model shapes or provenance expectations.
- Schema alignment risk — new persistence tables/JSONB fields must land before activities execute.

## Proof Strategy
- Workflow wiring risk → retire in S01 by proving intake activity + guarded transition reaches INTAKE_COMPLETE via real workflow.
- Fixture fidelity risk → retire in S02 by proving fixtures load and persist into JurisdictionResolution/RequirementSet with provenance fields.
- Schema alignment + cross-runtime risk → retire in S03 by proving docker-compose Postgres/Temporal runbook completes to RESEARCH_COMPLETE.

## Verification Classes
- Contract verification: Pydantic intake contract validation + fixture schema checks + model serialization tests.
- Integration verification: Temporal + Postgres integration tests driving API → worker → DB artifacts.
- Operational verification: docker-compose runbook proving full workflow progression with real services.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slice deliverables are complete and documented.
- Intake, jurisdiction, and requirements activities are wired into PermitCaseWorkflow with guard-mediated transitions.
- The real API entrypoint is exercised with a spec-derived intake payload and advances the workflow through RESEARCH_COMPLETE.
- Success criteria are re-checked against live docker-compose behavior (not just tests).
- Final integrated acceptance scenarios pass (PermitCase + Project + JurisdictionResolution + RequirementSet persisted).

## Requirement Coverage
- Covers: R010, R011, R012
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices
- [x] **S01: Intake contract + Project persistence + INTAKE_COMPLETE workflow step** `risk:high` `depends:[]`
  > After this: POSTing a spec-derived intake payload creates PermitCase + Project and the workflow reaches INTAKE_COMPLETE (verified via API/DB).
- [x] **S02: Jurisdiction + requirements fixtures, persistence, and workflow progression** `risk:medium` `depends:[S01]`
  > After this: the same case advances through JURISDICTION_COMPLETE and RESEARCH_COMPLETE with persisted JurisdictionResolution/RequirementSet artifacts and provenance inspectable via API/DB.
- [x] **S03: End-to-end docker-compose proof (API + worker + Postgres + Temporal)** `risk:low` `depends:[S01,S02]`
  > After this: the runbook + integration test prove a real workflow run progresses from intake to RESEARCH_COMPLETE with persisted artifacts using live services.

## Boundary Map
### S01 → S02
Produces:
- Intake API contract + endpoint returning `case_id`/`project_id`.
- Project persistence and intake activity that transitions case to INTAKE_COMPLETE via `apply_state_transition`.
- Workflow state: PermitCase in INTAKE_COMPLETE with associated Project row.

Consumes:
- nothing (first slice)

### S02 → S03
Produces:
- JurisdictionResolution + RequirementSet models/migrations with provenance JSONB payloads.
- Fixture loader + activities that persist jurisdiction/requirements and advance to JURISDICTION_COMPLETE + RESEARCH_COMPLETE.
- Read surfaces (API/DB queries) for persisted artifacts.

Consumes:
- Intake API + Project persistence + INTAKE_COMPLETE state from S01.
