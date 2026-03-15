---
estimated_steps: 8
estimated_files: 3
---

# T01: Add legal-hold schema + domain model

**Slice:** S03 — Retention + legal hold guardrails (INV-004) + purge denial tests
**Milestone:** M001-r2v2t3

## Description
Add durable legal-hold persistence and typed domain models so holds can be applied/queried by artifact stable ID.

## Steps
1. Read `invariants/sps/INV-004/invariant.yaml` and `runbooks/sps/legal-hold.md` to capture required semantics.
2. Extend DB models with `legal_holds` and hold bindings (artifact-scoped and/or case-scoped).
3. Add indexes to make hold lookup by artifact ID efficient.
4. Generate and audit Alembic migration.
5. Apply migrations against local Postgres.
6. Add a minimal unit/integration test proving holds can be inserted/read.
7. Add typed models in `src/sps/retention/models.py`.
8. Ensure metadata captures who/when/why.

## Must-Haves
- [ ] Schema supports legal holds and bindings.
- [ ] Migration applies cleanly.
- [ ] A test can insert/read a hold bound to an EvidenceArtifact stable ID.

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head`

## Inputs
- S01 migrations/models
- INV-004 + runbook semantics

## Expected Output
- `src/sps/db/models.py` — legal hold tables.
- `alembic/versions/*` — migration.
- `src/sps/retention/models.py` — domain models.
