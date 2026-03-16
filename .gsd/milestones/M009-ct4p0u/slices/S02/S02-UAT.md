# S02: Release Bundle and Blocker Gates — UAT

**Milestone:** M009-ct4p0u
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: release bundle gating depends on live Postgres + FastAPI endpoints and CLI execution with real manifest verification.

## Preconditions
- Docker services running: `docker compose up -d`
- Python venv installed at `.venv` with project deps.
- Migrations applied: `.venv/bin/alembic upgrade head`
- API running: `.venv/bin/uvicorn sps.api.main:app --port 8000`
- Reviewer key available: `export SPS_REVIEWER_API_KEY=dev-reviewer-key`

## Smoke Test
- Create a temp directory with a valid manifest and run:
  - `python scripts/generate_release_bundle.py --release-id UAT-SMOKE-001 --root <temp> --manifest PACKAGE-MANIFEST.json --dry-run`
  - **Expected:** CLI prints a JSON manifest payload and exits 0.

## Test Cases
### 1. Clean release bundle persists
1. Create a temp dir and generate a valid artifact + manifest:
   ```bash
   TMP_DIR=$(mktemp -d /tmp/m009_s02_uat_ok_XXXXXX)
   python - <<'PY'
import hashlib
import json
from pathlib import Path
root = Path("$TMP_DIR")
artifact = root / "artifact.yaml"
artifact.write_text("""---\nartifact_metadata:\n  artifact_id: ART-UAT-001\n---\nname: uat\n""", encoding="utf-8")
content = artifact.read_bytes()
manifest = [{"path": artifact.name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}]
(root / "PACKAGE-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
PY
   ```
2. Clear release tables + blockers:
   ```bash
   bash -c 'source scripts/lib/assert_postgres.sh; pg_exec "TRUNCATE TABLE release_artifacts, release_bundles, contradiction_artifacts, dissent_artifacts, review_decisions, permit_cases CASCADE"'
   ```
3. Run the CLI:
   `python scripts/generate_release_bundle.py --release-id UAT-REL-001 --root "$TMP_DIR" --manifest PACKAGE-MANIFEST.json --api-base http://localhost:8000 --reviewer-api-key "$SPS_REVIEWER_API_KEY"`
4. **Expected:** Exit 0; JSON response includes `bundle_id` and `release_id=UAT-REL-001`.

### 2. Manifest mismatch fails closed
1. Create a bad manifest:
   ```bash
   TMP_BAD=$(mktemp -d /tmp/m009_s02_uat_bad_XXXXXX)
   python - <<'PY'
import json
from pathlib import Path
root = Path("$TMP_BAD")
artifact = root / "artifact.yaml"
artifact.write_text("""---\nartifact_metadata:\n  artifact_id: ART-UAT-002\n---\nname: uat\n""", encoding="utf-8")
content = artifact.read_bytes()
manifest = [{"path": artifact.name, "sha256": "0" * 64, "bytes": len(content)}]
(root / "PACKAGE-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
PY
   ```
2. Run the CLI:
   `python scripts/generate_release_bundle.py --release-id UAT-REL-BAD --root "$TMP_BAD" --manifest PACKAGE-MANIFEST.json --api-base http://localhost:8000 --reviewer-api-key "$SPS_REVIEWER_API_KEY"`
3. **Expected:** Exit non-zero; stderr contains `release_bundle.manifest_invalid`.

### 3. Blocker failure
1. Insert a blocking contradiction + dissent:
   ```bash
   bash -c 'source scripts/lib/assert_postgres.sh; pg_exec "insert into permit_cases (case_id, tenant_id, project_id, case_state, review_state, submission_mode, portal_support_level, current_release_profile, legal_hold) values ('\''RUNBOOK-BLOCK-001'\'', '\''tenant-uat'\'', '\''project-RUNBOOK-BLOCK-001'\'', '\''REVIEW_PENDING'\'', '\''PENDING'\'', '\''DIGITAL'\'', '\''FULL'\'', '\''default'\'', false) on conflict (case_id) do nothing"'
   bash -c 'source scripts/lib/assert_postgres.sh; pg_exec "insert into review_decisions (decision_id, schema_version, case_id, object_type, object_id, decision_outcome, reviewer_id, subject_author_id, reviewer_independence_status, evidence_ids, contradiction_resolution, dissent_flag, notes, decision_at, idempotency_key) values ('\''RUNBOOK-DEC-001'\'', '\''1.0'\'', '\''RUNBOOK-BLOCK-001'\'', '\''permit_case'\'', '\''RUNBOOK-BLOCK-001'\'', '\''ACCEPT_WITH_DISSENT'\'', '\''reviewer-uat'\'', '\''author-uat'\'', '\''INDEPENDENT'\'', '{}', null, true, null, (now() - interval '\''1 day'\''), '\''runbook/RUNBOOK-DEC-001'\'') on conflict (decision_id) do nothing"'
   bash -c 'source scripts/lib/assert_postgres.sh; pg_exec "insert into dissent_artifacts (dissent_id, linked_review_id, case_id, scope, rationale, required_followup, resolution_state, created_at) values ('\''DISSENT-UAT-001'\'', '\''RUNBOOK-DEC-001'\'', '\''RUNBOOK-BLOCK-001'\'', '\''PERMIT/HIGH_RISK'\'', '\''rationale'\'', null, '\''OPEN'\'', now()) on conflict (dissent_id) do nothing"'
   bash -c 'source scripts/lib/assert_postgres.sh; pg_exec "insert into contradiction_artifacts (contradiction_id, case_id, scope, source_a, source_b, ranking_relation, blocking_effect, resolution_status, created_at) values ('\''CONTRA-UAT-001'\'', '\''RUNBOOK-BLOCK-001'\'', '\''RELEASE'\'', '\''source-a'\'', '\''source-b'\'', '\''SAME_RANK'\'', true, '\''OPEN'\'', now()) on conflict (contradiction_id) do nothing"'
   ```
2. Re-run the CLI from test case 1 (good manifest).
3. **Expected:** Exit non-zero; stderr includes `release_bundle.blocked` and lists blockers.

## Edge Cases
### Missing reviewer key
1. Unset `SPS_REVIEWER_API_KEY` and rerun the CLI against a valid manifest.
2. **Expected:** CLI exits non-zero with `release_bundle.post_failed` or `release_bundle.blocked` due to 401/403 from the API.

## Failure Signals
- CLI success path exits non-zero or prints `release_bundle.*` error on stderr.
- `GET /api/v1/ops/release-blockers` returns 500 or malformed payload.
- `release_bundles` table has no row after a reported success.

## Requirements Proved By This UAT
- R024 — Release bundle manifest generation (REL-001) via verified manifest + fail-closed gating.

## Not Proven By This UAT
- R025 — Rollback rehearsal evidence
- R026 — Post-release validation template/workflow
- Auth/RBAC hardening (M010)

## Notes for Tester
- The CLI requires live Postgres + API; run `docker compose up -d` before starting.
- Use the dev reviewer key (`dev-reviewer-key`) unless configured otherwise.
