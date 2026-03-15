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

## CI / integrity checks (local)

```bash
python -m pip install -e ".[dev]"
python tools/check_repo_wiring.py
python tools/verify_package_manifest.py
check-jsonschema --check-metaschema model/sps/contracts/*.schema.json
```
