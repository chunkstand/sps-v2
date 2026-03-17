# Architecture

**Analysis Date:** 2026-03-17

## Pattern Overview

**Overall:** Modular monolith with a layered FastAPI API and Temporal workflow orchestration.

**Key Characteristics:**
- HTTP API routes map Pydantic contracts to SQLAlchemy-backed persistence.
- Long-running state transitions are orchestrated in Temporal workflows with activities handling IO.
- Domain state is centralized in Postgres with explicit transition/audit ledgers.

## Layers

**API Layer:**
- Purpose: Expose HTTP endpoints and render lightweight pages.
- Location: `src/sps/api/`
- Contains: FastAPI app wiring, routes, response/request contracts, templates/static assets.
- Depends on: `src/sps/config.py`, `src/sps/auth/`, `src/sps/db/`, `src/sps/services/`, `src/sps/workflows/`
- Used by: Uvicorn entrypoint via `src/sps/api/main.py`.

**Auth & RBAC:**
- Purpose: JWT identity validation and role enforcement.
- Location: `src/sps/auth/`
- Contains: JWT parsing/validation and role guards.
- Depends on: `src/sps/config.py`
- Used by: API routes such as `src/sps/api/routes/cases.py`.

**Service Layer:**
- Purpose: Encapsulate admin/ops domain operations and DB mutation helpers.
- Location: `src/sps/services/`
- Contains: Intent/review workflows, release logic, ops metrics.
- Depends on: `src/sps/db/models.py`
- Used by: API routes like `src/sps/api/routes/admin_portal_support.py`.

**Workflow Orchestration:**
- Purpose: Temporal workflows for state machines and long-running processes.
- Location: `src/sps/workflows/`
- Contains: Workflows, activities, CLI tooling, worker bootstrapping.
- Depends on: `src/sps/db/`, `src/sps/guards/`, `src/sps/fixtures/`, `src/sps/audit/`
- Used by: API routes (start/signal), Temporal worker in `src/sps/workflows/worker.py`.

**Persistence Layer:**
- Purpose: Postgres access and ORM models.
- Location: `src/sps/db/`
- Contains: SQLAlchemy models, session factory, query helpers.
- Depends on: `src/sps/config.py`
- Used by: API routes, services, workflow activities.

**Storage Layer:**
- Purpose: S3-compatible object storage abstraction.
- Location: `src/sps/storage/`
- Contains: S3 client wrapper and integrity checks.
- Depends on: `src/sps/config.py`
- Used by: Evidence/document workflows and tests.

**Domain Support Modules:**
- Purpose: Shared domain primitives (evidence, documents, guards, retention, audit).
- Location: `src/sps/evidence/`, `src/sps/documents/`, `src/sps/guards/`, `src/sps/retention/`, `src/sps/audit/`
- Contains: Domain models, ID helpers, guard assertions, retention logic, audit event helpers.
- Depends on: `src/sps/db/`
- Used by: Workflows and services.

## Data Flow

**HTTP API Request (CRUD + workflow triggers):**

1. Request hits FastAPI router in `src/sps/api/routes/*.py`.
2. Request/response validation via Pydantic contracts in `src/sps/api/contracts/*.py`.
3. SQLAlchemy session from `src/sps/db/session.py` reads/writes `src/sps/db/models.py`.
4. For long-running processes, routes start or signal Temporal workflows in `src/sps/workflows/`.

**Temporal Workflow Execution:**

1. Worker `src/sps/workflows/worker.py` executes `PermitCaseWorkflow` in `src/sps/workflows/permit_case/workflow.py`.
2. Workflow schedules activities in `src/sps/workflows/permit_case/activities.py`.
3. Activities perform DB IO via `src/sps/db/session.py` and emit audit events via `src/sps/audit/events.py`.

**Evidence/Artifact Storage:**

1. Evidence metadata is stored in `src/sps/db/models.py` (`EvidenceArtifact`, `DocumentArtifact`).
2. Binary content is persisted or presigned through `src/sps/storage/s3.py`.

**State Management:**
- Authoritative state lives in Postgres tables in `src/sps/db/models.py`.
- Workflow orchestration state lives in Temporal (`src/sps/workflows/permit_case/workflow.py`).
- State transitions are recorded in `case_transition_ledger` via `src/sps/workflows/permit_case/activities.py`.

## Key Abstractions

**API Contracts (Pydantic):**
- Purpose: Explicit request/response schemas.
- Examples: `src/sps/api/contracts/cases.py`, `src/sps/api/contracts/reviews.py`
- Pattern: `BaseModel`-based contracts used by FastAPI routes.

**ORM Models (SQLAlchemy):**
- Purpose: Persisted domain entities and ledgers.
- Examples: `src/sps/db/models.py`
- Pattern: Declarative models with explicit tables and indexes.

**Temporal Workflow + Activities:**
- Purpose: Long-running state machines with deterministic logic.
- Examples: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`
- Pattern: Workflow orchestrates, activities perform IO and return typed results.

**Guard Assertions:**
- Purpose: Business invariant enforcement for state transitions.
- Examples: `src/sps/guards/guard_assertions.py`, `src/sps/workflows/permit_case/activities.py`
- Pattern: Structured denial results with guard assertion IDs.

## Entry Points

**FastAPI App:**
- Location: `src/sps/api/main.py`
- Triggers: Uvicorn/Gunicorn app import.
- Responsibilities: Configure logging, mount routes/static, expose health endpoints.

**Temporal Worker:**
- Location: `src/sps/workflows/worker.py`
- Triggers: `python -m sps.workflows.worker` or direct module execution.
- Responsibilities: Connect to Temporal, register workflows/activities, run polling loop.

**Workflow CLI:**
- Location: `src/sps/workflows/cli.py`
- Triggers: `python -m sps.workflows.cli`.
- Responsibilities: Start workflows and send review signals for operators.

## Error Handling

**Strategy:** Structured errors with logging at the boundary and re-raising in background tasks.

**Patterns:**
- Routes raise `HTTPException` after logging SQLAlchemy errors (example: `src/sps/api/routes/cases.py`).
- Activities catch and log exceptions with correlation IDs, then re-raise (`src/sps/workflows/permit_case/activities.py`).
- Workflow denials are returned as typed results rather than raising (`src/sps/workflows/permit_case/activities.py`).

## Cross-Cutting Concerns

**Logging:** Structured logging with redaction filter in `src/sps/logging/redaction.py`.
**Validation:** Pydantic models in `src/sps/api/contracts/` and workflow contracts in `src/sps/workflows/permit_case/contracts.py`.
**Authentication:** JWT identity + role checks in `src/sps/auth/identity.py` and `src/sps/auth/rbac.py`.

---

*Architecture analysis: 2026-03-17*
