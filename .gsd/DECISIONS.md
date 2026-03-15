# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| 1 | 2026-03-15 | repo | Monorepo implementation structure | Single Python monorepo | Simplifies shared types/contracts/invariants across services while we build Phase 1–3 foundations. | yes |
| 2 | 2026-03-15 | Phase 1 | API + persistence stack | FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + psycopg; S3 via boto3; local MinIO | Boring, well-supported stack; aligns with “typed schemas at trust boundaries” and supports integration testing against real Postgres/MinIO. | yes |
| 3 | 2026-03-15 | Phase 2 | Phase 2 proof strategy | Temporal harness + state transition guard proven via minimal end-to-end workflow; ReviewDecision injected via Temporal signal pre-M003 | Retires replay/guard risks early without forcing full domain implementation or reviewer service in Phase 2. | yes |
