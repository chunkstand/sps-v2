# M004-lp1flz: Phase 4 — intake, jurisdiction, and requirements workers — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement Phase 4 domain worker foundations for SPS: normalize intake into a Project, resolve jurisdiction stack/support level, and retrieve authoritative requirements with provenance. These workers will be wired into the existing PermitCaseWorkflow using real Postgres persistence and guard semantics, with spec-derived intake contracts and spec-sourced fixtures for initial authority data.

## Why This Milestone

Phase 4 begins the core domain pipeline that turns intake into actionable, governed artifacts. Without intake normalization, jurisdiction resolution, and authoritative requirements retrieval, later compliance, document generation, and submission milestones have no trusted inputs. This milestone establishes the earliest domain outputs while respecting the existing authority boundary and reviewer gates.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Submit a spec-derived intake payload and see a PermitCase + Project created and progressed through intake/jurisdiction/research states via the workflow.
- Inspect the persisted JurisdictionResolution and RequirementSet artifacts (with provenance) for a case using authoritative fixtures.

### Entry point / environment

- Entry point: `./.venv/bin/uvicorn sps.api.main:app` + `./.venv/bin/python -m sps.workflows.worker`
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, Temporal (Temporal UI optional)

## Completion Class

- Contract complete means: spec-derived intake contract validates; jurisdiction/requirement outputs match fixture schemas with provenance fields.
- Integration complete means: a real workflow run advances through INTAKE/JURISDICTION/RESEARCH states using the new activities and persists outputs in Postgres.
- Operational complete means: tests and runbook prove end-to-end behavior against docker-compose Postgres/Temporal.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A PermitCaseWorkflow run accepts intake, persists Project, and advances to JURISDICTION_COMPLETE with a persisted JurisdictionResolution.
- The same run reaches RESEARCH_COMPLETE with a persisted RequirementSet that includes ranked sources and provenance evidence.
- The above is proven against live docker-compose Postgres + Temporal (not mocked DB).

## Risks and Unknowns

- Fixture fidelity risk — if spec-sourced fixtures are incomplete, later compliance/document phases may need migration work.
- Workflow wiring risk — state transitions must remain deterministic and guarded as activities are added.

## Existing Codebase / Prior Art

- `src/sps/workflows/permit_case/workflow.py` — existing workflow orchestration to extend with new domain activities.
- `src/sps/workflows/permit_case/activities.py` — authoritative activity patterns and guard placement.
- `model/sps/model.yaml` — domain model definitions for Project/JurisdictionResolution/RequirementSet.
- `specs/sps/build-approved/spec.md` — normative domain requirements (F-001–F-003) and authority rules.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R010 — Intake normalization into Project (F-001) is implemented and persisted.
- R011 — Jurisdiction stack resolution (F-002) is implemented with support-level classification.
- R012 — Requirements retrieval with provenance (F-003) is implemented using ranked sources.

## Scope

### In Scope

- Spec-derived intake contract and API path to create PermitCase + Project.
- Intake, jurisdiction, and requirements worker activities wired into PermitCaseWorkflow.
- Spec-sourced fixture data for jurisdiction/requirements, with provenance fields.
- Postgres persistence for Project, JurisdictionResolution, and RequirementSet artifacts.
- Integration tests + operator runbook proving end-to-end workflow progression.

### Out of Scope / Non-Goals

- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).
- External API integrations for jurisdiction/requirements (fixtures only).
- Compliance evaluation, incentives, document generation, submission, or tracking.

## Technical Constraints

- Authoritative state mutation remains orchestrator/guard mediated.
- Reviewer gates remain required for protected transitions; no bypass via worker logic.
- Workflow code remains deterministic; all I/O via activities.

## Integration Points

- Postgres — authoritative persistence for Project/JurisdictionResolution/RequirementSet.
- Temporal — workflow orchestration and activity execution.
- Evidence registry — provenance/evidence IDs referenced in RequirementSet.

## Open Questions

- Where should fixture datasets live (specs/ vs new fixtures/ directory) to keep provenance clear? — decide during planning.
