# Codebase Structure

**Analysis Date:** 2026-03-17

## Directory Layout

```
[project-root]/
├── src/                 # Application source
│   └── sps/             # Core package
├── tests/               # Pytest suites and fixtures
├── alembic/             # Database migrations
├── scripts/             # Dev/verification scripts
├── docker/              # Container assets
├── ci/                  # CI definitions
├── diagrams/            # Architecture/process diagrams
├── specs/               # Specifications and standards
├── model/               # Domain model artifacts
├── runbooks/            # Operational runbooks
├── docker-compose.yml   # Local dev stack
├── pyproject.toml       # Python project config
└── alembic.ini          # Alembic configuration
```

## Directory Purposes

**src/sps:**
- Purpose: Application code for API, workflows, and domain logic.
- Contains: Modules for API routes, persistence, workflows, services, and shared utilities.
- Key files: `src/sps/api/main.py`, `src/sps/config.py`, `src/sps/db/models.py`

**src/sps/api:**
- Purpose: HTTP interface and lightweight pages.
- Contains: FastAPI app, routes, contracts, templates, static assets.
- Key files: `src/sps/api/main.py`, `src/sps/api/routes/cases.py`, `src/sps/api/contracts/cases.py`

**src/sps/workflows:**
- Purpose: Temporal workflows, activities, and worker entrypoints.
- Contains: Workflow definitions, activity implementations, worker/CLI wiring.
- Key files: `src/sps/workflows/worker.py`, `src/sps/workflows/permit_case/workflow.py`

**src/sps/db:**
- Purpose: SQLAlchemy models and session wiring.
- Contains: ORM models, session factory, query helpers.
- Key files: `src/sps/db/models.py`, `src/sps/db/session.py`

**src/sps/services:**
- Purpose: Domain service helpers for admin/ops flows.
- Contains: Intent/review helpers and admin metadata updates.
- Key files: `src/sps/services/admin_portal_support.py`

**src/sps/storage:**
- Purpose: Object storage adapter.
- Contains: S3 client wrapper and integrity checks.
- Key files: `src/sps/storage/s3.py`

**src/sps/documents:**
- Purpose: Document contract definitions and generation helpers.
- Contains: Contracts, registry, and generator utilities.
- Key files: `src/sps/documents/contracts.py`, `src/sps/documents/generator.py`

**src/sps/evidence:**
- Purpose: Evidence domain primitives and IDs.
- Contains: Evidence data models and ID helpers.
- Key files: `src/sps/evidence/models.py`, `src/sps/evidence/ids.py`

**src/sps/retention:**
- Purpose: Retention policy guards and purge logic.
- Contains: Retention guards and purge routines.
- Key files: `src/sps/retention/guard.py`, `src/sps/retention/purge.py`

**src/sps/audit:**
- Purpose: Audit event helpers for persistent logging.
- Contains: Audit event emitters.
- Key files: `src/sps/audit/events.py`

**tests:**
- Purpose: Pytest suite organized by milestone/test IDs.
- Contains: Integration and unit tests, fixtures, helper utilities.
- Key files: `tests/conftest.py`, `tests/m004_s01_intake_api_workflow_test.py`

**alembic:**
- Purpose: Database migrations and Alembic environment.
- Contains: Alembic env, migration templates, and versions.
- Key files: `alembic/env.py`, `alembic/versions/`

## Key File Locations

**Entry Points:**
- `src/sps/api/main.py`: FastAPI application and route mounting.
- `src/sps/workflows/worker.py`: Temporal worker process.
- `src/sps/workflows/cli.py`: Operator CLI for workflow start/signals.

**Configuration:**
- `pyproject.toml`: Project metadata and tooling config.
- `src/sps/config.py`: Application settings and environment vars.
- `alembic.ini`: Alembic migration settings.

**Core Logic:**
- `src/sps/workflows/permit_case/workflow.py`: Permit case workflow orchestration.
- `src/sps/workflows/permit_case/activities.py`: Workflow activities and guard logic.
- `src/sps/db/models.py`: Domain persistence models.

**Testing:**
- `tests/`: All test suites.
- `tests/fixtures/`: Test fixtures.
- `tests/helpers/`: Test utilities.

## Naming Conventions

**Files:**
- `snake_case.py` modules (example: `src/sps/workflows/permit_case/workflow.py`).
- Test files use milestone prefixes like `tests/m004_s01_intake_api_workflow_test.py` or `tests/s01_db_schema_test.py`.

**Directories:**
- Lowercase module names (example: `src/sps/api`, `src/sps/workflows`).

## Where to Add New Code

**New Feature:**
- Primary code: `src/sps/` submodule matching the domain (API: `src/sps/api/routes/`, workflows: `src/sps/workflows/`).
- Tests: `tests/` with milestone-style naming.

**New Component/Module:**
- Implementation: `src/sps/<module_name>/` with `__init__.py` and `snake_case.py` files.

**Utilities:**
- Shared helpers: `src/sps/` adjacent to related domain modules (for DB helpers use `src/sps/db/`).

## Special Directories

**src/sps/api/templates:**
- Purpose: Jinja2 templates for reviewer/ops pages.
- Generated: No
- Committed: Yes

**src/sps/api/static:**
- Purpose: Static assets for API pages.
- Generated: No
- Committed: Yes

**alembic/versions:**
- Purpose: Database migration scripts.
- Generated: Yes (by Alembic)
- Committed: Yes

**tests/fixtures:**
- Purpose: Test data and fixture setup utilities.
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-17*
