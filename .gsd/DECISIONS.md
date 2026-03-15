# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| 1 | 2026-03-15 | repo | Monorepo implementation structure | Single Python monorepo | Simplifies shared types/contracts/invariants across services while we build Phase 1–3 foundations. | yes |
| 2 | 2026-03-15 | Phase 1 | API + persistence stack | FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + psycopg; S3 via boto3; local MinIO | Boring, well-supported stack; aligns with “typed schemas at trust boundaries” and supports integration testing against real Postgres/MinIO. | yes |
| 3 | 2026-03-15 | Phase 2 | Phase 2 proof strategy | Temporal harness + state transition guard proven via minimal end-to-end workflow; ReviewDecision injected via Temporal signal pre-M003 | Retires replay/guard risks early without forcing full domain implementation or reviewer service in Phase 2. | yes |
| 4 | 2026-03-15 | Phase 1 | Evidence artifact stable IDs + object key layout | `artifact_id = ART-<ULID>`; object key `evidence/<ULID[:2]>/<artifact_id>` | Stable + sortable IDs without a central sequence; deterministic object keys avoid ambiguity and keep S3 prefixes partitioned. | yes |
| 5 | 2026-03-15 | Phase 1 | Readiness semantics (Phase 1) | `/readyz` returns 200 without probing Postgres | Avoid coupling service boot to infra availability while Phase 1 is focused on schema/migrations; deeper readiness checks can be added when APIs require DB connectivity. | yes |
| 6 | 2026-03-15 | Phase 1 | Migration configuration | Alembic env derives DB URL from `sps.config.Settings` (no DSN in `alembic.ini`) | Single source of truth for DB config across runtime, migrations, and tests; makes redaction/logging policy consistent. | yes |
| 7 | 2026-03-15 | Phase 1 | Phase 1 schema strategy | Stable-ID string primary keys + JSONB for nested/provenance-like fields | Keeps Phase 1 unblocked and avoids premature deep normalization before workflows and invariants stabilize. | yes |
| 8 | 2026-03-15 | Phase 2 | Guard placement for authoritative state | All PermitCase authoritative state transitions are evaluated + applied inside a Postgres transaction within a Temporal *activity* (workflow orchestrates only) | Keeps workflows deterministic/replay-safe and centralizes fail-closed governance at the DB authority boundary. | yes |
| 9 | 2026-03-15 | Phase 2 | Idempotency key for transition ledger | Use `StateTransitionRequest.request_id` as `case_transition_ledger.transition_id` (PK) and treat duplicate PK as “already applied” | Prevents duplicate side effects under activity retry; makes replay/idempotency provable with simple DB invariants. | yes |
