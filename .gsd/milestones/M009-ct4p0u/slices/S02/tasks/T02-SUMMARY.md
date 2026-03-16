---
id: T02
parent: S02
milestone: M009-ct4p0u
provides:
  - Release bundle manifest builder + CLI with blocker gating and runbook verification
key_files:
  - src/sps/services/release_bundle_manifest.py
  - scripts/generate_release_bundle.py
  - tests/m009_s02_release_bundle_test.py
  - scripts/verify_m009_s02.sh
  - src/sps/config.py
key_decisions:
  - None
patterns_established:
  - Release bundle CLI uses package-manifest verifier and explicit blocker gating with structured stderr errors
observability_surfaces:
  - CLI stderr/exit codes for manifest/blocker/post failures; runbook script output
duration: 2h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Build release bundle CLI, manifest assembly, and runbook verification

**Added a release bundle manifest builder and CLI that validates manifests, checks blockers, and posts bundles with runbook + tests covering success and failure paths.**

## What Happened
- Added a manifest builder that reads `PACKAGE-MANIFEST.json`, extracts artifact IDs/digests, and validates release bundle payloads against the schema.
- Implemented `scripts/generate_release_bundle.py` to run the package manifest verifier, gate on release blockers, and post bundles with structured failure messages plus an ASGI HTTP mode for integration tests.
- Expanded integration tests for CLI success, manifest mismatch, and blocker failure scenarios.
- Added runbook `scripts/verify_m009_s02.sh` to exercise success and failure paths with database seeding.
- Added release bundle defaults to `sps.config.Settings` for manifest version fields.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
- `bash scripts/verify_m009_s02.sh --failure-paths`
- `SPS_REVIEWER_API_KEY=dev-reviewer-key curl -s -H "X-Reviewer-Api-Key: $SPS_REVIEWER_API_KEY" http://localhost:8000/api/v1/ops/release-blockers | jq '.blockers'`

## Diagnostics
- CLI prints `release_bundle.manifest_invalid`, `release_bundle.blocked`, or `release_bundle.post_failed` with stderr details and non-zero exit codes.
- Runbook script logs and API log tail at `.gsd/runbook/m009_s02_api_*.log` on failure.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/services/release_bundle_manifest.py` — manifest builder with artifact digest extraction and schema validation.
- `scripts/generate_release_bundle.py` — release bundle CLI with blocker gating and ASGI test mode.
- `tests/m009_s02_release_bundle_test.py` — added CLI integration tests for success/mismatch/blocker scenarios.
- `scripts/verify_m009_s02.sh` — runbook verification script covering success and failure paths.
- `src/sps/config.py` — release bundle version defaults for manifest assembly.
- `.gsd/milestones/M009-ct4p0u/slices/S02/S02-PLAN.md` — updated verification steps and marked T02 complete.
