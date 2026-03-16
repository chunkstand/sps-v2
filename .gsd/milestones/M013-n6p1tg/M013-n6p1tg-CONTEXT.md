# M013-n6p1tg: Phase 13 — admin policy/config governance — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement governed admin policy/config mutation workflows. This milestone introduces explicit intent, review, and audit trails for admin changes (portal support metadata, source rules, incentive programs), with reviewer approval requirements and authoritative mutation paths.

## Why This Milestone

The spec requires admin changes to be governed with intent, review, and audit trails to prevent hidden authority drift. Without this milestone, policy/config updates risk bypassing reviewer and release controls.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Propose admin changes via an intent artifact, route them through review, and apply them via governed mutation paths.
- Inspect an audit trail for every admin change.

### Entry point / environment

- Entry point: admin config API + reviewer approval flow
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, reviewer API

## Completion Class

- Contract complete means: admin intent/change artifacts validate against spec/model shapes.
- Integration complete means: admin changes require review and are applied only via governed mutation paths.
- Operational complete means: tests and runbook prove intent → review → apply → audit trail.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Admin change intent is recorded and reviewed before applying.
- Applied changes are auditable and linked to reviewer decisions.
- Unauthorized admin mutations are denied.

## Risks and Unknowns

- Scope sprawl risk — keep admin change types limited to core policy/config surfaces.
- Review workflow alignment — ensure reviewer controls map correctly to admin changes.

## Existing Codebase / Prior Art

- `src/sps/api/routes/reviews.py` — reviewer decision authority boundary.
- `specs/sps/build-approved/spec.md` — admin governance requirements (section 5.5).

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R035 — Admin changes require intent/review/audit trail (spec section 5.5).

## Scope

### In Scope

- Admin intent artifacts and governed mutation paths.
- Reviewer approval requirement for admin changes.
- Audit trail persistence for admin changes.
- Integration tests + operator runbook proving end-to-end admin change governance.

### Out of Scope / Non-Goals

- Full admin UI dashboards.
- External configuration management integrations.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Admin changes must fail closed without valid approval.
- Workflow and policy enforcement must remain deterministic.

## Integration Points

- Postgres — admin intent/change persistence.
- Reviewer API — approvals for admin changes.

## Open Questions

- Which admin change types are mandatory in Phase 13? — decide during planning.
