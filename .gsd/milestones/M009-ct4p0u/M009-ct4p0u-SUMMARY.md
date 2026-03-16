---
id: M009-ct4p0u
provides:
  - audit event persistence and ops metrics dashboard for queue health signals
  - release bundle manifest validation with fail-closed blocker gating
  - rollback rehearsal evidence capture and post-release validation runbook template
key_decisions:
  - fail closed on release bundle creation when artifacts are stale or blockers are open
  - reuse EvidenceRegistry storage for rollback rehearsal artifacts
patterns_established:
  - ops metrics assembled via query helpers + service response builder
  - release bundle CLI verifies PACKAGE-MANIFEST.json before posting bundles
observability_surfaces:
  - audit_events table in Postgres
  - GET /api/v1/ops/dashboard/metrics + /ops dashboard
  - GET /api/v1/ops/release-blockers
  - GET /api/v1/evidence/artifacts/{artifact_id}
requirement_outcomes:
  - id: R022
    from_status: active
    to_status: validated
    proof: pytest tests/m009_s01_audit_events_test.py
  - id: R023
    from_status: active
    to_status: validated
    proof: pytest tests/m009_s01_dashboard_test.py
  - id: R024
    from_status: active
    to_status: validated
    proof: pytest tests/m009_s02_release_bundle_test.py + scripts/verify_m009_s02.sh
  - id: R025
    from_status: active
    to_status: validated
    proof: pytest tests/m009_s03_rollback_rehearsal_test.py + scripts/verify_m009_s03.sh
  - id: R026
    from_status: active
    to_status: validated
    proof: runbooks/sps/post-release-validation.md + scripts/verify_m009_s03.sh
duration: 8.6h
verification_result: passed
completed_at: 2026-03-16
---

# M009-ct4p0u: Phase 9 — release, rollback, and observability gates — Roadmap

**Audit events, minimal ops dashboards, release bundle gating, and rollback rehearsal evidence are now verified end-to-end for Phase 9 release readiness.**

## What Happened
We added audit event persistence for critical review/state actions, shipped a minimal ops dashboard backed by metrics API queries for queue depth/contradiction backlog/stalled reviews, and introduced release bundle gating with manifest validation that fails closed on stale artifacts or open blockers. Release bundles now persist artifact digests through the API, with blocker visibility via `/api/v1/ops/release-blockers`. We also implemented rollback rehearsal evidence capture via the existing evidence registry and shipped a stage-gated post-release validation runbook template with an operational verification script.

## Cross-Slice Verification
- Audit event persistence: `pytest tests/m009_s01_audit_events_test.py` proves audit rows with correlation/request metadata.
- Ops dashboard metrics: `pytest tests/m009_s01_dashboard_test.py` validates `/api/v1/ops/dashboard/metrics` and `/ops` page render.
- Release bundle creation + fail-closed gating: `pytest tests/m009_s02_release_bundle_test.py` and `scripts/verify_m009_s02.sh --failure-paths` verify manifest hashing, artifact mismatch denial, and blocker gating.
- Rollback rehearsal evidence: `pytest tests/m009_s03_rollback_rehearsal_test.py` validates checksum handling and evidence persistence.
- Post-release validation runbook: `scripts/verify_m009_s03.sh` confirms rollback rehearsal artifact retrieval and template presence.

## Requirement Changes
- R022: active → validated — `pytest tests/m009_s01_audit_events_test.py`.
- R023: active → validated — `pytest tests/m009_s01_dashboard_test.py`.
- R024: active → validated — `pytest tests/m009_s02_release_bundle_test.py` + `scripts/verify_m009_s02.sh`.
- R025: active → validated — `pytest tests/m009_s03_rollback_rehearsal_test.py` + `scripts/verify_m009_s03.sh`.
- R026: active → validated — `runbooks/sps/post-release-validation.md` + `scripts/verify_m009_s03.sh`.

## Forward Intelligence
### What the next milestone should know
- `/ops` renders without auth, but metrics and release blocker endpoints require the reviewer API key.
- Release bundle CLI requires a running API + Postgres to resolve blockers; no offline cache exists.
- Rollback rehearsal checksum validation canonicalizes JSON payloads (sorted keys + compact separators).

### What's fragile
- `/ops` dashboard JS depends on the `data-metrics-endpoint` attribute — template changes can break metrics loading silently.
- Release bundle manifest verification is strict; any `PACKAGE-MANIFEST.json` mismatch or missing artifact will fail closed.

### Authoritative diagnostics
- `audit_events` table and `GET /api/v1/ops/dashboard/metrics` — definitive signals for observability readiness.
- `GET /api/v1/ops/release-blockers` — authoritative release gating surface.
- `GET /api/v1/evidence/artifacts/{artifact_id}` — rollback rehearsal evidence verification.

### What assumptions changed
- Expected rollback rehearsal runbook to be self-starting; it now assumes a running API on port 8000.

## Files Created/Modified
- `src/sps/db/models.py` — AuditEvent ORM model.
- `src/sps/api/routes/ops.py` — ops metrics + release blocker endpoints.
- `src/sps/api/templates/ops/index.html` — ops dashboard template.
- `src/sps/api/static/ops.js` — metrics fetch/render logic.
- `src/sps/api/routes/releases.py` — release bundle + rollback rehearsal endpoints.
- `scripts/generate_release_bundle.py` — manifest validation + fail-closed bundle creation.
- `scripts/verify_m009_s02.sh` — release bundle runbook.
- `scripts/verify_m009_s03.sh` — rollback rehearsal + runbook verification.
- `runbooks/sps/post-release-validation.md` — post-release validation template.
