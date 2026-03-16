# M011-kg7s2p: Phase 11 — comment resolution, resubmission, and approval tracking — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement post-submission workflows: comment resolution and resubmission loops plus approval/inspection milestone tracking. This milestone wires these flows into PermitCaseWorkflow, consuming SubmissionAttempt and ExternalStatusEvent data from Phase 7 and persisting CorrectionTask, ResubmissionPackage, ApprovalRecord, and InspectionMilestone artifacts.

## Why This Milestone

After initial submission, SPS must handle review comments, resubmissions, and final approvals to complete the permit lifecycle. These flows are required for functional completeness and compliance with F-008/F-009.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Record review comments and see CorrectionTask + ResubmissionPackage artifacts generated and tracked through workflow.
- Persist approval records and inspection milestones as external status events arrive.

### Entry point / environment

- Entry point: API + worker workflow execution
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, Temporal

## Completion Class

- Contract complete means: CorrectionTask, ResubmissionPackage, ApprovalRecord, and InspectionMilestone artifacts validate against spec/model shapes.
- Integration complete means: a workflow run processes comment resolution and resubmission loops and records approvals/inspections.
- Operational complete means: tests and runbook prove end-to-end behavior against docker-compose Postgres/Temporal.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Comment resolution events generate correction tasks and resubmission packages with durable persistence.
- Resubmission attempts are recorded and workflow progresses accordingly.
- Approval and inspection milestones are persisted from normalized external status events.

## Risks and Unknowns

- Workflow complexity risk — resubmission loops can introduce state explosion; keep minimal loop to start.
- External status dependency risk — approvals tracking depends on normalized status mappings.

## Existing Codebase / Prior Art

- `src/sps/workflows/permit_case/workflow.py` — orchestration to extend with resubmission and approval paths.
- `model/sps/model.yaml` — CorrectionTask, ResubmissionPackage, ApprovalRecord, InspectionMilestone definitions.
- `specs/sps/build-approved/spec.md` — F-008/F-009 requirements.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R032 — Comment resolution and resubmission loops (F-008).
- R033 — Approval and inspection milestone tracking (F-009).

## Scope

### In Scope

- Comment resolution inputs → CorrectionTask + ResubmissionPackage generation.
- Resubmission workflow path with new SubmissionAttempt records.
- Approval and inspection milestone persistence from status events.
- Workflow wiring for comment/resubmission and approvals.
- Integration tests + operator runbook proving end-to-end workflow progression.

### Out of Scope / Non-Goals

- Advanced reviewer UI for comment triage.
- External portal integrations beyond fixture-based status events.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Workflow code remains deterministic; all I/O via activities.
- Authoritative state mutation remains orchestrator/guard mediated.

## Integration Points

- Postgres — authoritative persistence for correction/resubmission/approval artifacts.
- Temporal — workflow orchestration and activity execution.

## Open Questions

- How to model repeated resubmission loops without unbounded state growth? — decide during planning.
