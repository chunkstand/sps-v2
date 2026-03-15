# M001: Phase 1 — authoritative data foundations — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

## Project Description

Implement SPS v2.0.1 Phase 1 foundations: authoritative Postgres schema + evidence registry + retention/legal-hold guardrails, per:
- `specs/sps/build-approved/spec.md`
- `specs/sps/build-approved/runtime-implementation-profile.md`
- `specs/sps/build-approved/plan.md` (Phase 1)
- `specs/sps/build-approved/tasks.md` (Workstream B/C)

## Why This Milestone

Temporal workflows, reviewer gates, contradiction handling, and release bundles all rely on a durable authority model. Phase 1 builds the minimum authoritative substrate (schema + evidence registry) so later phases can be implemented as guarded workflows rather than ad-hoc state.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Bring up local infrastructure (Postgres + MinIO) and apply migrations.
- Register an EvidenceArtifact, upload its content to S3-compatible storage, and retrieve it by stable ID.
- Place a legal hold and prove purge/destructive delete is denied while the hold is active.

### Entry point / environment

- Entry point: FastAPI service (local) + CLI/scripts for migrations and demo calls
- Environment: local dev (`docker compose`)
- Live dependencies involved: Postgres, MinIO

## Completion Class

- Contract complete means: typed request/response + domain models validate inputs; stable ID shapes are enforced.
- Integration complete means: real Postgres + real MinIO roundtrip works end-to-end.
- Operational complete means: basic failure diagnostics exist (clear errors, invariant denial reasons); no daemon supervision requirements yet.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Evidence roundtrip: POST register → PUT upload → GET metadata → GET presigned download (or streamed content) works against local Postgres+MinIO.
- Legal hold: attempt to purge/delete held evidence fails closed and emits a clear, queryable failure reason.

## Risks and Unknowns

- Stable ID semantics and future compatibility — if we pick the wrong ID scheme, later release/audit reconstruction is painful.
- Evidence/content correlation — ensuring metadata and object content cannot silently diverge.
- Retention/legal-hold semantics — must align with INV-004 and runbook expectations.

## Existing Codebase / Prior Art

- `specs/sps/build-approved/plan.md` — Phase 1 objectives and exit criteria.
- `specs/sps/build-approved/tasks.md` — Workstream B/C task list.
- `invariants/sps/INV-004/invariant.yaml` and `runbooks/sps/legal-hold.md` — legal-hold requirements.
- `docker-compose.yml` — local Postgres/MinIO scaffold.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001 — schema/migrations for authoritative entities
- R002 — evidence registry by stable IDs
- R003 — legal hold prevents purge (INV-004)

## Scope

### In Scope

- Postgres schema + migrations for Phase 1 entities
- Evidence registry API + storage binding
- Legal hold + retention guardrails for evidence (INV-004)
- Tests proving integration roundtrip + legal-hold denial

### Out of Scope / Non-Goals

- Temporal workflows (Phase 2)
- Reviewer UI/service (Phase 3)
- Submission adapters and external status tracking (Phase 5)

## Technical Constraints

- Must remain consistent with SPS v2.0.1 canonical spec package.
- Must not log secrets (S3 creds, DB password).
- Use a single Python monorepo.

## Integration Points

- Postgres — authoritative relational store
- MinIO (S3-compatible) — evidence/artifact object storage

## Open Questions

- Evidence stable ID format: ULID vs UUIDv7 vs spec-defined. Current plan: ULID (lexicographically sortable) unless spec mandates otherwise during implementation.
