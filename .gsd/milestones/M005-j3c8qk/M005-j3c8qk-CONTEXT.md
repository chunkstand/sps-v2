# M005-j3c8qk: Phase 5 — compliance and incentives workers — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement Phase 5 domain workers for compliance evaluation and incentive assessment. This milestone consumes the Project, JurisdictionResolution, and RequirementSet outputs from Phase 4 and produces ComplianceEvaluation and IncentiveAssessment artifacts with rule results, blockers/warnings, and provenance, using fixture-based rule sets and a simple evaluator. Outputs are wired into PermitCaseWorkflow with real Postgres persistence and governed transitions.

## Why This Milestone

Phase 4 provides normalized intake, jurisdiction, and requirements, but the system still lacks compliance determinations and incentive findings. These artifacts are required before document generation and reviewer approval. This milestone establishes the rule-evaluation layer while keeping data sources fixture-based to avoid external integration risk.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run a PermitCaseWorkflow that advances through COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE with persisted ComplianceEvaluation and IncentiveAssessment artifacts.
- Inspect rule results, blockers/warnings, and provenance for the case using fixture-based rules.

### Entry point / environment

- Entry point: `./.venv/bin/uvicorn sps.api.main:app` + `./.venv/bin/python -m sps.workflows.worker`
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, Temporal (Temporal UI optional)

## Completion Class

- Contract complete means: compliance/incentive artifacts validate against spec/model shape with rule results and provenance fields populated.
- Integration complete means: a real workflow run advances through compliance and incentives states using the new activities and persists outputs in Postgres.
- Operational complete means: tests and runbook prove end-to-end behavior against docker-compose Postgres/Temporal.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A workflow run produces a ComplianceEvaluation with rule-by-rule results and persists it with case linkage.
- The same run produces an IncentiveAssessment with program eligibility outputs and persists it.
- The above is proven against live docker-compose Postgres + Temporal.

## Risks and Unknowns

- Rule fixture completeness — incomplete or inconsistent rule fixtures could force rework in later external integration phases.
- Evaluation determinism — rule evaluation must remain deterministic to preserve Temporal replay safety.

## Existing Codebase / Prior Art

- `src/sps/workflows/permit_case/workflow.py` — orchestration to extend with compliance/incentive activities.
- `src/sps/workflows/permit_case/activities.py` — authoritative activity patterns and guard placement.
- `model/sps/model.yaml` — ComplianceEvaluation and IncentiveAssessment definitions.
- `specs/sps/build-approved/spec.md` — normative requirements F-004 and F-005.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R013 — Compliance evaluation (F-004) is implemented and persisted.
- R014 — Incentive assessment (F-005) is implemented and persisted.

## Scope

### In Scope

- Fixture-based compliance rules and a simple deterministic evaluator.
- Incentive assessment outputs from fixture-based program rules/sources.
- Compliance and incentive worker activities wired into PermitCaseWorkflow.
- Postgres persistence for ComplianceEvaluation and IncentiveAssessment artifacts.
- Integration tests + operator runbook proving end-to-end workflow progression.

### Out of Scope / Non-Goals

- External rule engines or live code/requirements integrations.
- Document generation, submission, tracking, or release gating.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Workflow code remains deterministic; all I/O via activities.
- Authoritative state mutation remains orchestrator/guard mediated.

## Integration Points

- Postgres — authoritative persistence for ComplianceEvaluation/IncentiveAssessment.
- Temporal — workflow orchestration and activity execution.
- Evidence registry — provenance/evidence IDs referenced in rule results.

## Open Questions

- Where should compliance/incentive fixture datasets live to keep provenance clear? — decide during planning.
