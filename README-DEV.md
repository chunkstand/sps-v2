# SPS local development (scaffold)

This repo is seeded from the **SPS v2.0.1 BUILD_APPROVED** canonical spec package.

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

## CI / integrity checks (local)

```bash
python -m pip install -e ".[dev]"
python tools/check_repo_wiring.py
python tools/verify_package_manifest.py
check-jsonschema --check-metaschema model/sps/contracts/*.schema.json
```
