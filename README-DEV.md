# SPS local development

This repo is an application codebase for SPS. Some legacy spec-package assets remain in-tree for release validation and policy data, but day-to-day development should center on the app under `src/sps`, its migrations, and its tests.

## Local infra (Temporal + Postgres + MinIO)

Prereqs:
- Docker Desktop (or equivalent)
- `docker compose` v2

Start services:
```bash
docker compose up -d
```

Verify:
- Temporal UI: http://localhost:8080
- MinIO console: http://localhost:9001 (user/pass from `.env.example`)
- Postgres: `localhost:5432`

Stop:
```bash
docker compose down
```

## Run the application

Start the API:

```bash
uvicorn sps.api.main:app --reload
```

Useful endpoints:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/healthz
- Reviewer console: http://localhost:8000/reviewer-console

## Temporal demo (PermitCaseWorkflow)

Start the worker (terminal A):

```bash
python -m sps.workflows.worker
```

Start a workflow and then unblock it via signal (terminal B):

```bash
python -m sps.workflows.cli start --case-id CASE-<ULID>
python -m sps.workflows.cli signal-review --case-id CASE-<ULID> --decision-outcome APPROVE --reviewer-id reviewer-1
```

Notes:
- Stable workflow id convention: `permit-case/<case_id>`
- Inspect history in Temporal UI: http://localhost:8080

Integration proof (requires `docker compose up -d`):

```bash
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py
```

Test marker policy:
- Infra-backed tests must declare `@pytest.mark.integration` or `pytestmark = pytest.mark.integration`.
- Unmarked tests default to `unit` and must stay hermetic.

## Local checks

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -m "unit"
check-jsonschema --check-metaschema model/sps/contracts/*.schema.json
```

Optional release-bundle check:

```bash
python tools/verify_package_manifest.py
```

## Confidence pass

Bootstrap a fresh local environment:

```bash
scripts/bootstrap_dev.sh
```

Run the targeted confidence checks after local services are up:

```bash
docker compose up -d
scripts/run_confidence_checks.sh
```

Operator checklist: `runbooks/sps/confidence-checklist.md`
