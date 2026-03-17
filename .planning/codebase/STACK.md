# Technology Stack

**Analysis Date:** 2026-03-17

## Languages

**Primary:**
- Python >=3.11 - application and tooling in `pyproject.toml`, runtime code in `src/sps/api/main.py`

**Secondary:**
- YAML - spec/package assets in `specs/sps/build-approved/surface-policy.yaml` and `sps_full_spec_package/specs/sps/build-approved/surface-policy.yaml`

## Runtime

**Environment:**
- Python 3.11+ (project requirement) in `pyproject.toml`
- Python 3.12 (CI) in `.github/workflows/ci.yml`

**Package Manager:**
- pip (CI install path) in `.github/workflows/ci.yml`
- Lockfile: present (`uv.lock`)

## Frameworks

**Core:**
- FastAPI - API server and routing in `src/sps/api/main.py`
- SQLAlchemy - ORM and DB access in `src/sps/db/models.py` and `src/sps/db/session.py`
- Pydantic - settings and validation in `src/sps/config.py`
- Jinja2 - HTML templating via FastAPI templates in `src/sps/api/routes/reviewer_console.py`

**Testing:**
- pytest - test runner configured in `pyproject.toml` with tests in `tests/`

**Build/Dev:**
- hatchling - build backend in `pyproject.toml`
- ruff - linting/format settings in `pyproject.toml`
- Alembic - migrations configured in `alembic.ini`

## Key Dependencies

**Critical:**
- fastapi >=0.115.0 - API runtime in `pyproject.toml` and `src/sps/api/main.py`
- uvicorn[standard] >=0.30.0 - ASGI server in `pyproject.toml`
- sqlalchemy >=2.0.0 - DB layer in `pyproject.toml` and `src/sps/db/session.py`
- alembic >=1.13.0 - schema migrations in `pyproject.toml` and `alembic.ini`
- psycopg[binary] >=3.2.0 - PostgreSQL driver in `pyproject.toml`
- temporalio >=1.6.0 - workflow orchestration in `pyproject.toml` and `src/sps/workflows/temporal.py`
- boto3 >=1.34.0 - S3-compatible storage client in `pyproject.toml` and `src/sps/storage/s3.py`
- pyjwt >=2.8.0 - JWT validation in `pyproject.toml` and `src/sps/auth/identity.py`

**Infrastructure:**
- pydantic-settings >=2.3.0 - env-based config in `pyproject.toml` and `src/sps/config.py`
- jinja2 >=3.1.4 - HTML templates in `pyproject.toml` and `src/sps/api/routes/reviewer_console.py`
- ulid-py >=1.1.0 - stable identifiers in `pyproject.toml`

## Configuration

**Environment:**
- Settings via environment variables in `src/sps/config.py`
- Example env file present: `.env.example`

**Build:**
- Build config in `pyproject.toml`
- CI config in `.github/workflows/ci.yml`
- Local dependency stack defined (file exists) in `docker-compose.yml`

## Platform Requirements

**Development:**
- Python 3.11+ per `pyproject.toml`
- Postgres, Temporal, and S3-compatible storage expected by defaults in `src/sps/config.py`

**Production:**
- Not specified; configure via environment variables in `src/sps/config.py`

---

*Stack analysis: 2026-03-17*
