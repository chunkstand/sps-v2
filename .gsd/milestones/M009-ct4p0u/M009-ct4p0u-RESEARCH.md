# M009-ct4p0u: Phase 9 — release, rollback, and observability gates — Research

## Summary
The goal of Phase 9 is to fulfill Tier 3 compliance requirements by introducing an observability baseline (OBS-001, OBS-002, OBS-003) and release governance controls (REL-001, REL-002, REL-003).

Existing codebase patterns show that `ReleaseBundle` and `ReleaseArtifact` are already defined in the PostgreSQL schema, but `AuditEvent` is not. The system is heavily Postgres-authoritative. The most direct path to satisfying the "minimal sinks" requirement for audit events without adding infrastructure (like ELK/Grafana) is to introduce an `audit_events` Postgres table alongside structured logs, and expose a `/api/v1/ops/dashboard` FastAPI endpoint serving aggregated metrics. A Jinja-based UI `/ops` can consume this endpoint.

Release governance (REL-001) demands a "fail closed" approach on missing/stale generated binding artifacts, unresolved dissents on high-risk surfaces, and blocker contradictions. A Python CLI (`scripts/generate_release_bundle.py`) should handle this by:
1. Re-computing file hashes locally against `PACKAGE-MANIFEST.json` to prove no binding artifacts are stale.
2. Querying a new `GET /api/v1/ops/release-blockers` endpoint that checks `ContradictionArtifact` and `DissentArtifact` for open blockers.
3. Writing the compiled release bundle to `POST /api/v1/releases/bundles`.

Rollback rehearsal evidence (REL-002) can reuse the existing `sps.api.routes.evidence` registry by registering a new `ROLLBACK_REHEARSAL` artifact class. Finally, `runbooks/sps/post-release-validation.md` will fulfill REL-003 (post-release validation template).

## Strategic Questions & Recommendations
- **What should be proven first?** The `AuditEvent` schema and `/ops` dashboard should be proven first (M009/S01) to provide visibility into subsequent testing.
- **What existing patterns should be reused?** The `/reviewer` UI pattern (FastAPI HTMLResponse + Jinja templates) should be reused for the `/ops` dashboard. The `EvidenceRegistry` should be reused for rollback rehearsal artifacts.
- **What boundary contracts matter?** `ReleaseBundle` requires strict tracking of model versions, app versions, schema versions, and a list of artifacts. `PACKAGE-MANIFEST.json` is the source of truth for "binding artifacts" to be hash-checked.
- **Are there missing tables?** Yes. We need an `AuditEvent` model, and we need to add `ROLLBACK_REHEARSAL` to the `ArtifactClass` string enum.

## Don't Hand-Roll
| What | Why | Use Instead |
|---|---|---|
| A new log aggregator or metrics time-series DB | Local dev relies purely on Postgres/Minio/Temporal. Adding Prometheus/Grafana or ELK expands infrastructure unnecessarily for "minimal dashboards". | A Postgres `audit_events` table and a `GET /api/v1/ops/dashboard` JSON endpoint. |
| Complex UI framework | The spec dictates minimal observability. A full SPA or external metrics visualizer is scope creep. | Jinja2 templates served via FastAPI (mirroring the Phase 8 `reviewer_console` pattern). |
| A separate release metadata store | `ReleaseBundle` and `ReleaseArtifact` already exist in `sps.db.models`. | The existing Postgres tables `release_bundles` and `release_artifacts`. |

## Common Pitfalls
- **Silent release failures:** Ensure the release bundle script exits with non-zero status (`sys.exit(1)`) if a blocker contradiction is found or a hash mismatch occurs. The script must explicitly fail closed.
- **Missing correlation IDs in Audit Events:** OBS-001 specifically requires correlation fields. `AuditEvent` must include `event_id`, `correlation_id`, `actor_id`, and `resource_id`.
- **Dissent Scope Filtering:** Not *all* dissents block release, only "unresolved dissent on high-risk surfaces" (e.g. `scope` ending in `HIGH_RISK` or `AUTHORITY_BOUNDARY`). Be precise in the blocker query.

## Relevant Code
- `src/sps/db/models.py`: Contains `ReleaseBundle`, `ReleaseArtifact`, `ContradictionArtifact`, and `DissentArtifact`. Missing `AuditEvent`.
- `src/sps/evidence/models.py`: Missing `ROLLBACK_REHEARSAL` artifact class.
- `src/sps/api/routes/reviewer_console.py`: Jinja UI pattern for the dashboard.
- `PACKAGE-MANIFEST.json`: Binding artifacts reference file for REL-001.

## Proposed Candidate Slices
- [ ] **S01: Audit Events and Minimal Dashboards** `risk:low` `depends:[]`
  - Implement `AuditEvent` table and migration.
  - Expose `GET /api/v1/ops/dashboard/metrics` (queue depth, contradiction backlog, stalled reviews, etc.).
  - Add `/ops` Jinja page.
- [ ] **S02: Release Bundle and Blocker Gates** `risk:med` `depends:[S01]`
  - Expose `GET /api/v1/ops/release-blockers` and `POST /api/v1/releases/bundles`.
  - Create CLI `scripts/generate_release_bundle.py` that verifies hashes against `PACKAGE-MANIFEST.json` and posts the bundle if no blockers exist.
- [ ] **S03: Rollback Rehearsal and Post-Release Validation** `risk:low` `depends:[S02]`
  - Add `ROLLBACK_REHEARSAL` to `ArtifactClass`.
  - Expose `POST /api/v1/releases/rollbacks/rehearsals`.
  - Create `runbooks/sps/post-release-validation.md`.
