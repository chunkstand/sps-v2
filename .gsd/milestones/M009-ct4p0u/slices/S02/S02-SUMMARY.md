---
id: S02
parent: M009-ct4p0u
milestone: M009-ct4p0u
provides:
  - Release bundle persistence + blocker gating via API and CLI with manifest validation
requires:
  - slice: S01
    provides: audit events + ops dashboard metrics
affects:
  - S03
key_files:
  - src/sps/db/queries/release_blockers.py
  - src/sps/services/release_blockers.py
  - src/sps/api/routes/ops.py
  - src/sps/api/routes/releases.py
  - src/sps/services/release_bundle_manifest.py
  - scripts/generate_release_bundle.py
  - scripts/verify_m009_s02.sh
  - tests/m009_s02_release_bundle_test.py
key_decisions:
  - None
patterns_established:
  - Fail-closed release bundle creation (manifest verification + blocker gating before POST)
observability_surfaces:
  - GET /api/v1/ops/release-blockers (reviewer key)
  - release_bundle.* structured logs for create/invalid artifact paths
  - CLI stderr/exit codes for manifest/blocker/post failures
  - scripts/verify_m009_s02.sh runbook output + API log capture
drill_down_paths:
  - .gsd/milestones/M009-ct4p0u/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009-ct4p0u/slices/S02/tasks/T02-SUMMARY.md
duration: 3.5h
verification_result: passed
completed_at: 2026-03-16
---

# S02: Release Bundle and Blocker Gates

**Release bundle CLI + APIs now persist release bundles with verified artifact digests and block releases on open contradictions/dissents.**

## What Happened
- Implemented release blocker query/service layers and a reviewer-authenticated `/api/v1/ops/release-blockers` endpoint for open contradictions and dissents.
- Added `POST /api/v1/releases/bundles` to validate artifact digests and persist `release_bundles` + `release_artifacts` with explicit timestamps.
- Built a release bundle manifest builder + CLI that verifies `PACKAGE-MANIFEST.json`, checks blockers, and fails closed before posting bundles.
- Added integration tests and an operational runbook to cover success + failure paths (manifest mismatch, open blockers).

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
- `bash scripts/verify_m009_s02.sh --failure-paths`
- `curl -H "X-Reviewer-Api-Key: dev-reviewer-key" http://localhost:8000/api/v1/ops/release-blockers | jq`

## Requirements Advanced
- None

## Requirements Validated
- R024 — Release bundle manifest generation (REL-001) proven via integration tests + runbook CLI execution with success and fail-closed scenarios.

## New Requirements Surfaced
- None

## Requirements Invalidated or Re-scoped
- None

## Deviations
None.

## Known Limitations
- Release bundle endpoints rely on reviewer API key auth only; full auth/RBAC hardening remains in M010.
- CLI requires a running API + Postgres to resolve blockers; no offline blocker cache is implemented.

## Follow-ups
None.

## Files Created/Modified
- `src/sps/db/queries/release_blockers.py` — release blocker queries for contradictions/dissents.
- `src/sps/services/release_blockers.py` — blocker response builder and models.
- `src/sps/api/routes/ops.py` — release blockers endpoint.
- `src/sps/api/routes/releases.py` — bundle POST endpoint with artifact validation.
- `src/sps/services/release_bundle_manifest.py` — manifest builder + validation.
- `scripts/generate_release_bundle.py` — CLI for manifest verification, blocker gating, bundle submission.
- `scripts/verify_m009_s02.sh` — runbook script covering success/failure paths.
- `tests/m009_s02_release_bundle_test.py` — integration coverage for bundles + blockers.

## Forward Intelligence
### What the next slice should know
- The release blockers endpoint expects live Postgres and reviewer API key auth; use docker compose + dev key for UAT and runbooks.

### What's fragile
- Package manifest verification: any mismatch in `PACKAGE-MANIFEST.json` or artifacts causes fail-closed CLI exits, so keep fixtures aligned.

### Authoritative diagnostics
- `GET /api/v1/ops/release-blockers` — authoritative blocker surface when release gating fails.
- `scripts/verify_m009_s02.sh` logs and `.gsd/runbook/m009_s02_api_*.log` — fastest signal for release bundle failures.

### What assumptions changed
- None.
