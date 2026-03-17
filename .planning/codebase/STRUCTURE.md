# Codebase Structure

**Analysis Date:** 2026-03-17

## Directory Layout

```
[project-root]/
├── src/                  # Application source code
│   └── sps/              # Primary Python package
├── tests/                # Pytest test suite
├── alembic/              # DB migrations
├── invariants/           # Canonical invariant packs and guard assertions
├── model/                # Schema and contract artifacts
├── docker/               # Local/container runtime assets
├── ci/                   # CI scripts and configuration helpers
├── scripts/              # Developer and ops scripts
├── tools/                # Tooling helpers
├── diagrams/             # Architecture diagrams
├── runbooks/             # Operational runbooks
└── .planning/            # GSD planning artifacts
```

## Directory Purposes

**src/sps/api:**
- Purpose: HTTP API surface and FastAPI app wiring.
- Contains: `main.py`, routers, contracts, templates/static assets.
- Key files: `src/sps/api/main.py`, `src/sps/api/routes/`, `src/sps/api/contracts/`.

**src/sps/workflows:**
- Purpose: Temporal workflows, activities, and worker/CLI entry points.
- Contains: `worker.py`, `cli.py`, workflow modules.
- Key files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`.

**src/sps/db:**
- Purpose: Persistence layer and session helpers.
- Contains: SQLAlchemy models and session utilities.
- Key files: `src/sps/db/models.py`, `src/sps/db/session.py`.

**src/sps/services:**
- Purpose: Domain services used by routes and workflows.
- Contains: Service modules for admin/ops use cases.
- Key files: `src/sps/services/admin_portal_support.py`.

**src/sps/auth:**
- Purpose: Authentication and RBAC enforcement.
- Contains: Identity validation and role guard helpers.
- Key files: `src/sps/auth/rbac.py`, `src/sps/auth/identity.py`.

**src/sps/storage:**
- Purpose: Object storage adapter.
- Contains: S3-compatible wrapper.
- Key files: `src/sps/storage/s3.py`.

**src/sps/audit:**
- Purpose: Audit event emission.
- Contains: Audit event persistence helpers.
- Key files: `src/sps/audit/events.py`.

**src/sps/logging:**
- Purpose: Logging utilities and redaction.
- Contains: Redaction filter and helpers.
- Key files: `src/sps/logging/redaction.py`.

**src/sps/guards:**
- Purpose: Guard assertion to invariant mapping.
- Contains: YAML registry loader.
- Key files: `src/sps/guards/guard_assertions.py`.

**src/sps/evidence:**
- Purpose: Evidence artifact contracts and IDs.
- Contains: Pydantic models for evidence artifacts.
- Key files: `src/sps/evidence/models.py`, `src/sps/evidence/ids.py`.

**src/sps/documents:**
- Purpose: Document registry and generation helpers.
- Contains: Document contracts, registry, generator.
- Key files: `src/sps/documents/contracts.py`, `src/sps/documents/generator.py`.

**src/sps/retention:**
- Purpose: Retention policy models and guards.
- Contains: Retention models and purge helpers.
- Key files: `src/sps/retention/models.py`, `src/sps/retention/guard.py`.

**tests:**
- Purpose: Pytest test suite aligned to spec slices and workflows.
- Contains: Scenario tests, fixtures, helpers.
- Key files: `tests/conftest.py`, `tests/m004_s01_intake_api_workflow_test.py`.

## Key File Locations

**Entry Points:**
- `src/sps/api/main.py`: FastAPI application instance.
- `src/sps/workflows/worker.py`: Temporal worker runner.
- `src/sps/workflows/cli.py`: Operator CLI for workflows.

**Configuration:**
- `src/sps/config.py`: Settings and environment configuration.
- `alembic.ini`: Alembic configuration.

**Core Logic:**
- `src/sps/workflows/permit_case/workflow.py`: Primary case workflow orchestration.
- `src/sps/workflows/permit_case/activities.py`: Persistence and transition activities.

**Testing:**
- `tests/`: Primary test directory.
- `tests/fixtures/`: Test data fixtures.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py` (e.g., `src/sps/api/routes/admin_portal_support.py`).
- Tests use descriptive `*_test.py` naming with milestone/slice prefixes (e.g., `tests/m004_s01_intake_api_workflow_test.py`).

**Directories:**
- Package and module directories are lowercase (e.g., `src/sps/workflows/`, `src/sps/api/`).

## Where to Add New Code

**New Feature:**
- Primary code: `src/sps/services/` for domain operations or `src/sps/workflows/` for orchestration.
- Tests: `tests/` with a new `*_test.py` file matching existing naming patterns.

**New Component/Module:**
- Implementation: `src/sps/<component>/` with a new `snake_case.py` module.

**Utilities:**
- Shared helpers: `src/sps/` root modules (e.g., `src/sps/logging/`, `src/sps/guards/`).

## Special Directories

**alembic/:**
- Purpose: Alembic migrations.
- Generated: Yes (migration scripts).
- Committed: Yes.

**invariants/:**
- Purpose: Canonical invariant definitions used by guard assertions.
- Generated: No.
- Committed: Yes.

**.planning/:**
- Purpose: GSD planning artifacts and codebase maps.
- Generated: Yes.
- Committed: Yes.

---

*Structure analysis: 2026-03-17*
