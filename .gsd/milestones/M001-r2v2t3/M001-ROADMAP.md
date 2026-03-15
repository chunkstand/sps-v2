# M001: Phase 1 — authoritative data foundations

**Vision:** SPS has durable authoritative persistence and an evidence registry with stable IDs + legal-hold guardrails, so later workflows and reviewer gates can be implemented as governed state transitions.

## Success Criteria

- Migrations apply cleanly against local Postgres, producing the Phase 1 tables for PermitCase/Project/reviews/contradictions/transition ledger/evidence.
- Evidence artifacts can be registered and retrieved by stable ID, and content is stored in S3-compatible storage with integrity checks.
- Legal hold prevents purge/destructive delete of held evidence (INV-004) with a clear failure reason.

## Key Risks / Unknowns

- Stable ID scheme and object-store key layout could become a long-term compatibility hazard.
- Schema drift from `model/sps/model.yaml` could cause later guard or workflow mismatches.
- Retention/legal hold semantics must align with runbooks and compliance expectations.

## Proof Strategy

- Stable schema + migrations → retire in S01 by proving real Postgres migrations + smoke CRUD.
- Evidence roundtrip → retire in S02 by proving register/upload/retrieve/download against MinIO.
- Legal-hold enforcement → retire in S03 by proving purge/delete fails closed under hold with negative tests.

## Verification Classes

- Contract verification: pytest unit tests for Pydantic models + invariants helpers.
- Integration verification: pytest integration tests against docker-compose Postgres + MinIO.
- Operational verification: basic error surfaces (HTTP 4xx with invariant denial details; structured log lines), none beyond that in M001.
- UAT / human verification: none.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables are complete.
- The evidence registry service is actually wired to Postgres + MinIO (not mocked) and exercised end-to-end.
- The real entrypoint exists and is exercised: `uvicorn sps.api.main:app` (or equivalent) + curl/pytest integration.
- Success criteria are re-checked against live behavior, not just artifacts.
- Final integrated acceptance scenarios pass (evidence roundtrip + legal hold denial).

## Requirement Coverage

- Covers: R001, R002, R003
- Partially covers: none
- Leaves for later: reviewer gating, Temporal workflows, release bundle validation, submission adapters
- Orphan risks: none

## Slices

- [x] **S01: Postgres schema + migrations + typed model package** `risk:high` `depends:[]`
  > After this: local Postgres schema can be migrated and queried; typed models validate core entities.
- [ ] **S02: Evidence registry API + MinIO content roundtrip** `risk:high` `depends:[S01]`
  > After this: evidence can be registered, uploaded, and retrieved by stable ID end-to-end.
- [ ] **S03: Retention + legal hold guardrails (INV-004) + purge denial tests** `risk:medium` `depends:[S02]`
  > After this: legal-hold is enforced and destructive operations fail closed with diagnostic detail.

## Boundary Map

### S01 → S02

Produces:
- Alembic migrations + SQLAlchemy models for evidence metadata
- DB access layer + config loading
- Base FastAPI app skeleton (health, dependency wiring)

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- Evidence registry endpoints and object storage binding
- Stable ID generation and object key layout

Consumes:
- DB schema + models + migrations

