---
estimated_steps: 5
estimated_files: 4
---

# T02: Provision docker-compose Temporal environment + execute deferred S01 tests

**Slice:** S02 — Status event workflow wiring + live docker-compose runbook
**Milestone:** M011-kg7s2p

## Description

Provision a local Temporal + Postgres development environment using docker-compose, verify alembic migrations run cleanly, seed minimal fixture data to unblock S01 integration test FK dependencies, and execute the two deferred S01 integration tests (tests/m011_s01_status_event_artifacts_test.py and tests/m011_s01_resubmission_workflow_test.py) to prove the infrastructure and tests are ready.

## Steps

1. Verify docker-compose.yml has postgres (port 5432), temporal (port 7233), temporal-ui (port 8080), minio (ports 9000/9001) services configured with init scripts (docker/postgres/init/00-init.sql for database creation)
2. Write scripts/start_temporal_dev.sh: runs docker compose up -d, waits for Temporal readiness (retry loop: nc -z localhost 7233 || sleep 1, max 30 attempts), waits for Postgres readiness (docker compose exec postgres pg_isready retry loop), runs alembic upgrade head via docker compose exec postgres (or via host alembic with SPS_DB_DSN pointing to localhost:5432), exits 0 when services are ready
3. Seed minimal SubmissionPackage + EvidenceArtifact fixture rows to unblock tests/m011_s01_status_event_artifacts_test.py FK dependencies: create fixture script (tests/fixtures/seed_submission_package.py) that inserts a stub EvidenceArtifact row (artifact_id=ART-FIXTURE-001, artifact_class=SUBMISSION_MANIFEST, object_key=evidence/FI/ART-FIXTURE-001) and SubmissionPackage row (package_id=PKG-FIXTURE-001, case_id=CASE-EXAMPLE-001, submission_attempt_id=SUBM-EXAMPLE-001, manifest_artifact_id=ART-FIXTURE-001) into the test database; call this from conftest.py or directly in the test setup
4. Run pytest tests/m011_s01_status_event_artifacts_test.py -v with SPS_DB_DSN=postgresql://sps:sps@localhost:5432/sps to verify the test passes against live Postgres
5. Run SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s with SPS_TEMPORAL_ADDRESS=localhost:7233 and SPS_DB_DSN=postgresql://sps:sps@localhost:5432/sps to verify the test passes against live Temporal + Postgres; leave docker-compose services running for T03 runbook

## Must-Haves

- [ ] scripts/start_temporal_dev.sh provisions docker-compose services and waits for Temporal + Postgres readiness
- [ ] Alembic migrations run successfully via docker exec or host alembic against localhost:5432
- [ ] Minimal SubmissionPackage + EvidenceArtifact fixture data seeded to unblock tests/m011_s01_status_event_artifacts_test.py FK constraints
- [ ] pytest tests/m011_s01_status_event_artifacts_test.py -v passes against live Postgres
- [ ] SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s passes against live Temporal + Postgres

## Verification

- `bash scripts/start_temporal_dev.sh` exits 0 and leaves postgres/temporal/temporal-ui/minio services running
- `docker compose ps` shows all services running (Up status)
- `curl http://localhost:8080` returns Temporal UI (200 response)
- `docker compose exec postgres psql -U sps -d sps -c '\dt'` shows all Alembic-migrated tables (permit_cases, correction_tasks, resubmission_packages, etc.)
- `pytest tests/m011_s01_status_event_artifacts_test.py -v` passes with 0 failures
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s` passes with 0 failures

## Observability Impact

- Signals added/changed: docker-compose service logs (postgres init, temporal server startup, minio startup); alembic migration output (revision applied, tables created); pytest test output (test names, assertion results)
- How a future agent inspects this: docker compose logs postgres to see init script execution; docker compose logs temporal to verify server startup; docker compose exec postgres psql to query tables; curl http://localhost:8080 to verify Temporal UI; nc -z localhost 7233 to verify Temporal gRPC port
- Failure state exposed: scripts/start_temporal_dev.sh logs readiness check failures (Temporal port not ready after 30 retries, Postgres pg_isready failures); alembic upgrade errors logged to stdout; pytest failures include assertion details and traceback

## Inputs

- `docker-compose.yml` — existing docker-compose configuration with postgres + temporal + temporal-ui + minio services
- `docker/postgres/init/00-init.sql` — idempotent database/role creation script
- `alembic/versions/*` — all existing Alembic migrations including b1c2d3e4f5a6_post_submission_artifacts.py from S01
- `tests/m011_s01_status_event_artifacts_test.py` — deferred S01 integration test for artifact persistence (requires database setup)
- `tests/m011_s01_resubmission_workflow_test.py` — deferred S01 Temporal integration test for resubmission workflow (requires Temporal server + Postgres)
- `scripts/verify_m010_s03.sh` — reference runbook showing docker exec postgres psql pattern for assertions

## Expected Output

- `scripts/start_temporal_dev.sh` — provisions docker-compose services with readiness checks and alembic migrations
- `tests/fixtures/seed_submission_package.py` (or inline in conftest.py) — seeds minimal SubmissionPackage + EvidenceArtifact rows for test FK dependencies
- docker-compose services running and ready (postgres port 5432, temporal port 7233, temporal-ui port 8080)
- Alembic migrations applied (all tables exist in sps database)
- tests/m011_s01_status_event_artifacts_test.py passing (artifact persistence proven)
- tests/m011_s01_resubmission_workflow_test.py passing (workflow resubmission loop proven)
