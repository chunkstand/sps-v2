# M009-ct4p0u: Phase 9 — release, rollback, and observability gates — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement release/rollback gates and core observability requirements. This milestone delivers audit event schema and sinks, minimal dashboards/alerts, release bundle manifest generation, rollback rehearsal evidence capture, and post-release validation templates. It depends on prior milestones to produce domain artifacts and evidence required for release bundles.

## Why This Milestone

Tier 3 compliance requires release gating, rollback rehearsal, and observable audit trails. Without these, SPS cannot safely progress to production and lacks the mandatory release artifacts specified by the BUILD_APPROVED package.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Generate a release bundle manifest with required digests and compatibility checks.
- Produce rollback rehearsal evidence and a post-release validation template.
- Query audit events and view minimal dashboards/alerts for key operational signals.

### Entry point / environment

- Entry point: release bundle CLI/scripts + audit event sinks
- Environment: local dev + CI
- Live dependencies involved: Postgres, artifact storage, CI

## Completion Class

- Contract complete means: release/rollback artifacts and audit event schemas validate against spec.
- Integration complete means: release bundle + rollback rehearsal + post-release validation are produced from real artifacts.
- Operational complete means: runbooks and tests demonstrate release gating checks and minimal observability alerts.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Release bundle manifest generation succeeds and references current artifacts with digests.
- Rollback rehearsal evidence is produced and stored as required.
- Audit events are emitted and queryable, with minimal dashboards/alerts operational.

## Risks and Unknowns

- Artifact completeness risk — missing upstream artifacts can block release bundle generation.
- Observability scope risk — dashboards/alerts could sprawl; keep minimal.

## Existing Codebase / Prior Art

- `specs/sps/build-approved/spec.md` — release/rollback/observability requirements and artifact contracts.
- `traceability/sps/traceability.yaml` — binding artifacts and coverage mapping.
- `src/sps/api/routes/evidence.py` — evidence registry for release artifacts.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R022 — Audit event schema and sinks (OBS-001).
- R023 — Dashboards and alerts (OBS-002/OBS-003).
- R024 — Release bundle manifest generation (REL-001).
- R025 — Rollback rehearsal evidence (REL-002).
- R026 — Post-release validation template/workflow (REL-003).

## Scope

### In Scope

- Audit event schema + sinks, minimal dashboards/alerts.
- Release bundle manifest generation with compatibility checks.
- Rollback rehearsal artifact + evidence capture.
- Post-release validation template and stage-gated checks.
- Integration tests + operator runbooks.

### Out of Scope / Non-Goals

- Full observability suite beyond minimal dashboards/alerts.
- External incident/ticketing system integration.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Release gating must fail closed when artifacts are missing or stale.
- Audit events must include correlation fields per spec.

## Integration Points

- Postgres — audit event persistence and release metadata.
- Evidence registry — release/rollback artifacts.
- CI — release gating checks.

## Open Questions

- Which minimal dashboard set is required to satisfy OBS-002/003 without scope creep? — decide during planning.
