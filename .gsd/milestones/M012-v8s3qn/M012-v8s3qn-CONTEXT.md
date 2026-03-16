# M012-v8s3qn: Phase 12 — emergency and override governance — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement GOV-005 emergency declaration and override workflows with time-bounded artifacts, enforced in workflow/guard paths. This milestone introduces explicit emergency/override records, enforcement guards, and operator runbooks for bounded exception handling without silent authority drift.

## Why This Milestone

The spec requires emergency and override handling to be explicit, time-bounded, and non-normalizing. Without this milestone, SPS lacks governed exception paths for real-world incidents while preserving auditability and compliance.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Declare an emergency with bounded scope and see PermitCase enter EMERGENCY_HOLD or override mode with durable artifacts.
- Observe that overrides expire or require re-approval, and workflow/guard behavior reflects the declared state.

### Entry point / environment

- Entry point: emergency/override APIs + worker workflow execution
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, Temporal

## Completion Class

- Contract complete means: emergency/override artifacts validate against spec/model shapes and time-bound rules.
- Integration complete means: workflow/guards enforce emergency/override states in real runs.
- Operational complete means: tests and runbook prove declaration, enforcement, expiration, and audit behavior.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Emergency declaration creates durable artifacts and places cases in bounded emergency/override state.
- Overrides are time-bounded; expiration or re-approval is enforced and auditable.
- Workflow and guards reflect emergency/override conditions without silent state mutation.

## Risks and Unknowns

- Policy complexity risk — emergency paths can bypass normal gates; must remain explicitly bounded.
- Operator misuse risk — ensure runbooks make forbidden actions clear.

## Existing Codebase / Prior Art

- `src/sps/guards/guard_assertions.py` — guard assertion wiring for governance denials.
- `specs/sps/build-approved/spec.md` — GOV-005 requirements and emergency handling rules.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R034 — Emergency and override workflows are time-bounded and enforced (GOV-005).

## Scope

### In Scope

- Emergency declaration and override artifacts with time bounds.
- Workflow/guard enforcement for emergency/override conditions.
- Integration tests + operator runbook proving declaration, enforcement, and expiration behavior.

### Out of Scope / Non-Goals

- Broad policy redefinitions beyond emergency/override handling.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Exception handling must fail closed outside explicit emergency/override artifacts.
- Workflow code remains deterministic; all I/O via activities.

## Integration Points

- Postgres — authoritative persistence for emergency/override artifacts.
- Temporal — workflow orchestration and guard enforcement.

## Open Questions

- Which emergency durations and renewal policies should be defaulted in local dev? — decide during planning.
