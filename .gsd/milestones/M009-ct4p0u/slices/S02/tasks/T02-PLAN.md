---
estimated_steps: 5
estimated_files: 5
---

# T02: Build release bundle CLI, manifest assembly, and runbook verification

**Slice:** S02 — Release Bundle and Blocker Gates
**Milestone:** M009-ct4p0u

## Description
Create the release bundle generator CLI that validates the package manifest, checks release blockers, assembles the release manifest, and posts to the API; add tests and the runbook script.

## Steps
1. Implement a release bundle manifest builder that reads `PACKAGE-MANIFEST.json`, applies version fields from settings, and validates against the schema.
2. Implement `scripts/generate_release_bundle.py` to invoke the existing package manifest verifier, call the blockers endpoint, and fail closed on mismatches or blockers before posting bundles.
3. Add integration tests covering success, hash mismatch, and open blocker scenarios.
4. Add `scripts/verify_m009_s02.sh` to exercise the CLI success + failure paths with clear exit codes.
5. Ensure CLI errors include actionable messages (blocker IDs, manifest mismatch details).

## Must-Haves
- [ ] CLI exits non-zero on manifest mismatch or open blockers and surfaces the reason.
- [ ] Release manifest includes required version fields and artifact digests.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
- `bash scripts/verify_m009_s02.sh`

## Observability Impact
- Signals added/changed: CLI stderr output and exit codes on release gate failures
- How a future agent inspects this: run `scripts/generate_release_bundle.py --help` and `scripts/verify_m009_s02.sh`
- Failure state exposed: explicit mismatch/blocker messages and non-zero exit status

## Inputs
- `tools/verify_package_manifest.py` — existing fail-closed manifest verifier
- `model/sps/contracts/release-bundle-manifest.schema.json` — authoritative schema

## Expected Output
- `src/sps/services/release_bundle_manifest.py` — manifest builder
- `scripts/generate_release_bundle.py` — release bundle CLI
- `tests/m009_s02_release_bundle_test.py` — integration tests
- `scripts/verify_m009_s02.sh` — runbook verification script
