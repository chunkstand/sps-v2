# S02: Workflow document stage + end-to-end package runbook — Research

**Date:** 2026-03-16

## Summary

S02 must prove end-to-end document package generation with live infrastructure: docker-compose orchestrating Postgres, Temporal, and MinIO; workflow advancing from INTAKE_COMPLETE through DOCUMENT_COMPLETE; and package/manifest retrieval via API. S01 completed all implementation work (document generator, package persistence, workflow wiring, API endpoints) but couldn't prove full end-to-end behavior because integration tests hit S3 connection failures (no LocalStack/MinIO running during pytest). The docker-compose.yml already provisions all required services (postgres, temporal, temporal-ui, minio, minio-init with bucket creation), and the runbook pattern is well-established from M002/S03 through M005/S03.

Primary recommendation: write a runbook script following the M005/S03 pattern that (1) brings up docker-compose services, (2) applies migrations, (3) starts the FastAPI server, (4) clears Phase 6 fixture artifacts, (5) POSTs intake to create a case, (6) starts the worker with Phase 6 fixture override enabled, (7) waits for workflow to reach DOCUMENT_COMPLETE, (8) verifies package/manifest existence in Postgres + evidence_artifacts table, (9) calls GET /api/v1/cases/{case_id}/package and GET /api/v1/cases/{case_id}/manifest to prove API retrieval, and (10) verifies manifest digest consistency with evidence registry. This proves R015 end-to-end with live S3 (MinIO) and completes the milestone.

## Recommendation

Follow the M005/S03 runbook pattern exactly: orchestrate docker-compose services, start API + worker processes, drive the workflow through fixture-override intake, and assert end state with Postgres + API reads. This avoids hand-rolling infrastructure orchestration and reuses the proven `scripts/lib/assert_postgres.sh` helpers for safe DB assertions. The only new additions are: (a) Phase 6 fixture cleanup (delete by artifact IDs), (b) package/manifest API assertions, and (c) digest consistency checks between SubmissionPackage rows and evidence_artifacts checksums.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Docker compose orchestration + readiness | `scripts/verify_m005_s03.sh` pattern with `_wait_for_tcp` | Proven TCP-level readiness checks for Postgres/Temporal; avoids racy startup failures. |
| Safe Postgres assertions | `scripts/lib/assert_postgres.sh` (`pg_exec`, `pg_assert_int_eq`, `pg_print`) | Redacts credentials, runs psql inside docker container, provides operator-friendly errors. |
| Fixture case_id extraction + cleanup | `$PYTHON - <<'PY'...` heredocs in M005/S03 | Deterministic fixture ID extraction without adding CLI tools; keeps cleanup idempotent. |
| API server + worker lifecycle | `uvicorn ... & API_PID=$!` + `_cleanup()` trap pattern | Ensures background processes are killed on exit/signal; provides log diagnostics on failure. |

## Existing Code and Patterns

- `docker-compose.yml` — already provisions postgres, temporal, temporal-ui, minio (with minio-init service that creates sps-evidence/sps-release buckets); no changes needed.
- `scripts/verify_m005_s03.sh` — 680-line reference runbook showing docker compose orchestration, API/worker startup, fixture override env vars, workflow polling, Postgres assertions, and API read surfaces; serves as template for M006/S02.
- `scripts/lib/assert_postgres.sh` — provides `pg_exec`, `pg_assert_int_eq`, `pg_print`, `pg_sql_quote` helpers that run psql inside the docker container without exposing credentials; use these for all DB assertions.
- `src/sps/fixtures/phase6.py` — `select_document_fixtures()` returns fixture case_id and rewrites runtime case_id when `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE` is set; supports the same override pattern as Phase 4/5.
- `src/sps/workflows/permit_case/workflow.py` — already wired to call `persist_submission_package` activity and transition INCENTIVES_COMPLETE → DOCUMENT_COMPLETE; workflow returns after DOCUMENT_COMPLETE (no further transitions needed in S02).
- `src/sps/api/routes/cases.py` — GET `/cases/{case_id}/package` and GET `/cases/{case_id}/manifest` endpoints already implemented; return SubmissionPackageResponse and SubmissionManifestResponse with digests.
- `specs/sps/build-approved/fixtures/phase6/documents.json` — Phase 6 fixture dataset with case_id `CASE-EXAMPLE-001` (same as used in S01 tests); contains document definitions + manifest structure.

## Constraints

- Workflow determinism: the runbook must not inject non-deterministic state into the workflow; all fixture override happens via env vars before worker starts.
- MinIO readiness: `minio-init` service is a one-shot that exits after bucket creation; docker-compose must include `depends_on: minio` for the init service, and the runbook must ensure MinIO is TCP-reachable before starting the worker (use `_wait_for_tcp localhost 9000 30`).
- Fixture artifact cleanup strategy (from decision #70): delete by fixture artifact IDs (not just case_id) before reusing fixture override; fixture IDs are stable across runs and prevent idempotent insert conflicts.
- Package persistence idempotency: `persist_submission_package` activity is idempotent on `request_id`; if the runbook reruns, the second persist call should return the same package_id (proven in S01 test but not yet in runbook).

## Common Pitfalls

- **Skipping MinIO TCP check** — if the worker starts before MinIO is ready, `persist_submission_package` will fail with connection refused and the workflow will crash; add `_wait_for_tcp localhost 9000 30` after docker-compose up.
- **Not clearing fixture document/manifest artifacts** — Phase 6 fixtures have stable artifact IDs; if the runbook reruns without cleanup, evidence registry inserts will hit IntegrityError on artifact_id PK; extract fixture artifact IDs from documents.json and delete from evidence_artifacts before intake.
- **Assuming workflow continues to REVIEW_PENDING** — workflow currently stops at DOCUMENT_COMPLETE and returns; S02 runbook should assert DOCUMENT_COMPLETE as the final state, not wait for REVIEW_PENDING.
- **Forgetting manifest digest consistency check** — the critical proof for R015 is that `submission_packages.manifest_sha256_digest` matches `evidence_artifacts.checksum` for the manifest artifact; runbook should assert this equality via SQL join.

## Open Risks

- Digest determinism under Temporal retries — if an activity retry occurs after manifest registration but before DB commit, could the manifest artifact_id or digest change? Mitigation: S01 already proved deterministic digest computation from fixture bytes; activity idempotency ensures the same artifact_id is returned on retry (evidence registry checks for existing artifact_id before insert).
- MinIO bucket initialization race — if the runbook checks MinIO TCP port before `minio-init` completes bucket creation, the worker might fail with "bucket not found" during S3 put; mitigation: add a small sleep after MinIO TCP check or verify bucket existence via `mc ls` (but `minio-init` uses `mc mb -p` which is idempotent, so this should be rare).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (3.1K installs) |
| MinIO | vm0-ai/vm0-skills@minio | available (73 installs) |
| Bash shell scripting | miles990/claude-software-skills@shell-bash | available (13 installs) |

Note: The temporal-python-testing skill was used in prior milestones and is already proven. The MinIO skill may help with any S3 diagnostics if the runbook encounters bucket/object issues. Bash shell skill is optional since the runbook pattern is well-established from M005/S03.

## Sources

- Workflow wiring with persist_submission_package activity (source: `src/sps/workflows/permit_case/workflow.py` lines 542-570)
- Package/manifest API endpoints already implemented (source: `src/sps/api/routes/cases.py` lines 250-310)
- Phase 6 fixture structure with case_id and document artifact IDs (source: `specs/sps/build-approved/fixtures/phase6/documents.json`)
- Docker-compose MinIO service with bucket initialization (source: `docker-compose.yml` lines 38-62)
- Prior runbook pattern for fixture override + workflow assertions (source: `scripts/verify_m005_s03.sh`)
- Safe Postgres assertion helpers (source: `scripts/lib/assert_postgres.sh`)
- S01 forward intelligence noting S3 infrastructure requirement for full proof (source: `.gsd/milestones/M006-h7v2qk/slices/S01/S01-SUMMARY.md` Known Limitations section)
