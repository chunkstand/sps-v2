# Architecture

**Analysis Date:** 2026-03-17

## Pattern Overview

**Overall:** Modular monolith with FastAPI HTTP layer, Temporal workflow orchestration, and SQLAlchemy persistence (`src/sps/api/main.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/db/models.py`).

**Key Characteristics:**
- HTTP API routes are thin controllers that validate inputs via Pydantic contracts and orchestrate DB/workflow calls (`src/sps/api/routes/cases.py`, `src/sps/api/contracts/cases.py`).
- Long-running state transitions are modeled as Temporal workflows with activities as determinism boundaries (`src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`).
- Persistence is centralized in SQLAlchemy models and DB session helpers (`src/sps/db/models.py`, `src/sps/db/session.py`).

## Layers

**HTTP API Layer:**
- Purpose: Expose REST endpoints, enforce auth, and shape responses.
- Location: `src/sps/api/routes/`
- Contains: FastAPI routers, route handlers, HTTPException handling.
- Depends on: DB session (`src/sps/db/session.py`), services (`src/sps/services/`), workflows (`src/sps/workflows/`), auth (`src/sps/auth/`).
- Used by: `src/sps/api/main.py` includes routers.

**Contracts/DTO Layer:**
- Purpose: Define request/response schemas and workflow payload contracts.
- Location: `src/sps/api/contracts/`, `src/sps/workflows/permit_case/contracts.py`
- Contains: Pydantic models and enums for API and workflow messaging.
- Depends on: Pydantic base models.
- Used by: API routes and workflow/activity implementations.

**Auth Layer:**
- Purpose: Identity validation and role-based access control.
- Location: `src/sps/auth/`
- Contains: JWT validation and role guards.
- Depends on: Settings (`src/sps/config.py`).
- Used by: API routes via FastAPI dependencies (`src/sps/api/routes/*.py`).

**Service Layer:**
- Purpose: Encapsulate reusable domain operations beyond route logic.
- Location: `src/sps/services/`
- Contains: DB-oriented operations and domain-specific helpers.
- Depends on: SQLAlchemy models (`src/sps/db/models.py`).
- Used by: API routes (e.g., admin flows).

**Workflow Orchestration Layer:**
- Purpose: Orchestrate multi-step, long-running case transitions.
- Location: `src/sps/workflows/permit_case/workflow.py`
- Contains: Temporal workflow class and state machine logic.
- Depends on: Workflow contracts (`src/sps/workflows/permit_case/contracts.py`).
- Used by: API routes starting workflows and CLI/worker entry points (`src/sps/api/routes/cases.py`, `src/sps/workflows/cli.py`, `src/sps/workflows/worker.py`).

**Activities/Side-Effect Layer:**
- Purpose: Execute non-deterministic I/O (DB writes, storage, audits).
- Location: `src/sps/workflows/permit_case/activities.py`
- Contains: Temporal activities for persistence and state transitions.
- Depends on: DB session maker (`src/sps/db/session.py`), audit events (`src/sps/audit/events.py`).
- Used by: Temporal worker (`src/sps/workflows/worker.py`) and workflow (`src/sps/workflows/permit_case/workflow.py`).

**Persistence Layer:**
- Purpose: Define and access Postgres data models.
- Location: `src/sps/db/models.py`
- Contains: SQLAlchemy model definitions for core entities.
- Depends on: SQLAlchemy.
- Used by: API routes, services, and activities.

**Storage Layer:**
- Purpose: Object storage adapter for evidence and release artifacts.
- Location: `src/sps/storage/s3.py`
- Contains: S3-compatible client wrapper with integrity checks.
- Depends on: Settings (`src/sps/config.py`).
- Used by: Evidence-related logic and tests (e.g., `tests/s02_storage_adapter_test.py`).

**Guard/Invariant Layer:**
- Purpose: Map guard assertions to invariant IDs for workflow enforcement.
- Location: `src/sps/guards/guard_assertions.py`
- Contains: Guard assertion registry loader and lookup helpers.
- Depends on: Invariant registry files (`invariants/sps/guard-assertions.yaml`).
- Used by: Workflow activities (`src/sps/workflows/permit_case/activities.py`).

**Observability/Audit Layer:**
- Purpose: Record audit events and redact secrets from logs.
- Location: `src/sps/audit/events.py`, `src/sps/logging/redaction.py`
- Contains: Audit event emitter and log redaction filter.
- Depends on: SQLAlchemy session (`src/sps/db/models.py`).
- Used by: API routes and activities.

## Data Flow

**Case Intake → Workflow Start:**

1. HTTP POST `/cases` handled by FastAPI route (`src/sps/api/routes/cases.py`).
2. Route validates request via Pydantic contract (`src/sps/api/contracts/intake.py`).
3. Route writes `PermitCase` and `Project` rows via SQLAlchemy session (`src/sps/db/models.py`, `src/sps/db/session.py`).
4. Route starts Temporal workflow for the case (`src/sps/workflows/permit_case/workflow.py`) via client helper (`src/sps/workflows/temporal.py`).

**External Status Event → Persistence + Workflow Signal:**

1. HTTP POST `/cases/{case_id}/external-status-events` handled by FastAPI route (`src/sps/api/routes/cases.py`).
2. Route persists event via activity-style helper (`src/sps/workflows/permit_case/activities.py`).
3. Route signals running workflow with `StatusEventSignal` (`src/sps/workflows/permit_case/contracts.py`).

**Workflow Transition → DB + Audit:**

1. Workflow executes activity to apply guarded transitions (`src/sps/workflows/permit_case/workflow.py`).
2. Activity writes transition rows and emits audit events (`src/sps/workflows/permit_case/activities.py`, `src/sps/audit/events.py`).
3. Activity returns results to workflow for branching (`src/sps/workflows/permit_case/contracts.py`).

**State Management:**
- Authoritative state stored in Postgres tables (`src/sps/db/models.py`).
- Workflow state modeled via `CaseState` enums and workflow signals (`src/sps/workflows/permit_case/contracts.py`).

## Key Abstractions

**Pydantic Contracts:**
- Purpose: Validate and serialize API and workflow payloads.
- Examples: `src/sps/api/contracts/cases.py`, `src/sps/workflows/permit_case/contracts.py`.
- Pattern: `BaseModel` with `ConfigDict(extra="forbid")` for strict schemas.

**SQLAlchemy Models:**
- Purpose: Data persistence layer for domain entities.
- Examples: `src/sps/db/models.py`.
- Pattern: `DeclarativeBase` models with typed `Mapped` columns.

**Temporal Workflow + Activities:**
- Purpose: Orchestrate long-running case lifecycle transitions.
- Examples: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`.
- Pattern: Workflow orchestrates; activities execute I/O and return typed results.

**Storage Adapter:**
- Purpose: Consistent S3-compatible storage with integrity checks.
- Examples: `src/sps/storage/s3.py`.
- Pattern: Wrapper class returning typed `PutResult` and raising domain errors.

**Guard Assertion Registry:**
- Purpose: Map guard assertion IDs to invariant IDs for enforcement.
- Examples: `src/sps/guards/guard_assertions.py`, `invariants/sps/guard-assertions.yaml`.
- Pattern: Cached YAML registry lookup.

## Entry Points

**FastAPI app:**
- Location: `src/sps/api/main.py`
- Triggers: ASGI server (e.g., uvicorn) imports `app`.
- Responsibilities: Configure logging, mount static, include routers, health checks.

**Temporal worker:**
- Location: `src/sps/workflows/worker.py`
- Triggers: `python -m sps.workflows.worker` (module entry point).
- Responsibilities: Connect to Temporal, register workflows and activities.

**Workflow operator CLI:**
- Location: `src/sps/workflows/cli.py`
- Triggers: `python -m sps.workflows.cli`.
- Responsibilities: Start workflows and send signals.

## Error Handling

**Strategy:** Raise HTTPException in routes, log and re-raise in activities/workflows (`src/sps/api/routes/*.py`, `src/sps/workflows/permit_case/activities.py`).

**Patterns:**
- API routes catch SQLAlchemy errors and map to HTTP codes (`src/sps/api/routes/cases.py`).
- Activities log contextual IDs and propagate exceptions for Temporal retries (`src/sps/workflows/permit_case/activities.py`).

## Cross-Cutting Concerns

**Logging:** Redaction filter applied to root logger to avoid leaking secrets (`src/sps/logging/redaction.py`, `src/sps/api/main.py`).
**Validation:** Pydantic contracts enforce strict payload shapes for HTTP and workflow messages (`src/sps/api/contracts/*.py`, `src/sps/workflows/permit_case/contracts.py`).
**Authentication:** JWT and role-based access via FastAPI dependencies (`src/sps/auth/rbac.py`, `src/sps/api/routes/*.py`).

---

*Architecture analysis: 2026-03-17*
