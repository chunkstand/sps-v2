# Technology Stack

**Analysis Date:** 2026-03-17

## Languages

**Primary:**
- Python >=3.11 - application code and tooling (`pyproject.toml`, `src/sps/api/main.py`)

**Secondary:**
- Not detected

## Runtime

**Environment:**
- Python >=3.11 (`pyproject.toml`)

**Package Manager:**
- uv (version not detected) (`uv.lock`)
- Lockfile: present (`uv.lock`)

## Frameworks

**Core:**
- FastAPI >=0.115.0 - API framework (`pyproject.toml`, `src/sps/api/main.py`)
- SQLAlchemy >=2.0.0 - ORM/data access (`pyproject.toml`, `src/sps/db/session.py`)
- Pydantic >=2.7.0 - settings/validation (`pyproject.toml`, `src/sps/config.py`)

**Testing:**
- Pytest >=8.0.0 - test runner (`pyproject.toml`, `tests/m009_s01_dashboard_test.py`)

**Build/Dev:**
- Uvicorn >=0.30.0 - ASGI server (`pyproject.toml`, `src/sps/api/main.py`)
- Alembic >=1.13.0 - database migrations (`pyproject.toml`, `alembic.ini`)
- Ruff >=0.6.0 - linting (`pyproject.toml`)
- Hatchling >=1.24 - build backend (`pyproject.toml`)

## Key Dependencies

**Critical:**
- temporalio >=1.6.0 - workflow orchestration (`pyproject.toml`, `src/sps/workflows/temporal.py`)
- boto3 >=1.34.0 - S3-compatible object storage (`pyproject.toml`, `src/sps/storage/s3.py`)
- psycopg >=3.2.0 - Postgres driver (`pyproject.toml`, `src/sps/config.py`)

**Infrastructure:**
- PyJWT >=2.8.0 - JWT validation (`pyproject.toml`, `src/sps/auth/identity.py`)
- Jinja2 >=3.1.4 - server-side templates (`pyproject.toml`, `src/sps/api/routes/ops.py`)
- ulid-py >=1.1.0 - stable IDs (`pyproject.toml`, `src/sps/evidence/ids.py`)

## Configuration

**Environment:**
- Pydantic Settings with env var aliases (`src/sps/config.py`)
- `.env.example` present for reference (contents not read) (`.env.example`)

**Build:**
- Project config and deps (`pyproject.toml`)
- Dependency lockfile (`uv.lock`)
- Alembic migrations config (`alembic.ini`)
- Local infra orchestration file present (contents not read) (`docker-compose.yml`)
- CI policy artifact (`ci/sps/merge-authorization.yaml`)

## Platform Requirements

**Development:**
- Python >=3.11 (`pyproject.toml`)
- PostgreSQL (via SQLAlchemy/psycopg) (`src/sps/db/session.py`, `src/sps/config.py`)
- Temporal server (workflow runtime) (`src/sps/workflows/temporal.py`, `src/sps/config.py`)
- S3-compatible object storage (MinIO in local defaults) (`src/sps/storage/s3.py`, `src/sps/config.py`)

**Production:**
- Not detected

---

*Stack analysis: 2026-03-17*
