# GSD Phase 0 — repo bootstrap (SPS v2.0.1)

This file is an execution checklist for the Phase 0 goals in:
- `specs/sps/build-approved/plan.md` (Phase 0)
- `specs/sps/build-approved/tasks.md` (Workstream A)

## Outcome
- Canonical spec package paths exist at repo root (spec section 30).
- CI validates package integrity + schema metaschema.
- Local dev infra scaffold exists (Temporal + Postgres + S3-compatible).

## What was wired
### Canonical package
Paths are now at repo root:
- `specs/sps/build-approved/*`
- `model/sps/*`
- `invariants/sps/*`
- `traceability/sps/*`
- `runbooks/sps/*`
- etc.

### CI
- `.github/workflows/ci.yml`
- `tools/check_repo_wiring.py`
- `tools/verify_package_manifest.py`

### Local dev infra
- `docker-compose.yml`
- `docker/postgres/init/00-init.sql`
- `.env.example`
- `README-DEV.md`

## Executor runbook
### 1) (Local) Create a venv
macOS Homebrew Python is PEP-668 managed; use a venv:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

### 2) Run integrity checks
```bash
python tools/check_repo_wiring.py
python tools/verify_package_manifest.py
check-jsonschema --check-metaschema model/sps/contracts/*.schema.json
```

### 3) Start local infra
```bash
cp .env.example .env
docker compose up -d
```

Verify:
- Temporal UI: http://localhost:8080
- MinIO console: http://localhost:9001

Stop:
```bash
docker compose down
```
