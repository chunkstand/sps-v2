# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

**Files:**
- snake_case module names (Python standard), with domain segments under `src/sps/` (examples: `src/sps/api/routes/cases.py`, `src/sps/workflows/permit_case/contracts.py`)
- tests follow scenario-driven filenames like `tests/m004_s01_intake_api_workflow_test.py` and sequence-style files like `tests/s01_db_schema_test.py`

**Functions:**
- snake_case, private helpers prefixed with `_` (examples: `_send_status_event_signal` in `src/sps/api/routes/cases.py`, `_redact_url_password` in `src/sps/config.py`)

**Variables:**
- snake_case for locals and parameters; module constants in UPPER_SNAKE_CASE (examples: `STALLED_REVIEW_THRESHOLD` in `src/sps/services/ops_metrics.py`, `_CASE_ID_PREFIX` in `src/sps/api/routes/cases.py`)

**Types:**
- PascalCase for classes and Enums (examples: `PermitCase` in `src/sps/db/models.py`, `CaseState` in `src/sps/workflows/permit_case/contracts.py`)
- Enum values in UPPER_SNAKE_CASE (example: `CaseState.INTAKE_COMPLETE` in `src/sps/workflows/permit_case/contracts.py`)

## Code Style

**Formatting:**
- Tool: Ruff line-length configuration
- Key settings: `line-length = 100` in `pyproject.toml`

**Linting:**
- Tool: Ruff configured via `pyproject.toml` (no standalone `.ruff.toml` detected)

## Import Organization

**Order:**
1. Standard library imports
2. Third-party dependencies
3. Local package imports

Example ordering with blank-line separation in `src/sps/api/routes/cases.py` and `src/sps/services/ops_metrics.py`.

**Path Aliases:**
- Use absolute package imports from `sps.*` (example: `from sps.db.session import get_db` in `src/sps/api/routes/cases.py`)

## Error Handling

**Patterns:**
- API routes catch database exceptions and convert to `HTTPException` with structured error payloads (example: `src/sps/api/routes/cases.py` uses `except SQLAlchemyError` → `HTTPException(status_code=500, detail={...})`).
- Domain-specific validation uses `ValueError`/`LookupError` mapped to HTTP 409/404 with logging (example: `persist_external_status_event` handling in `src/sps/api/routes/cases.py`).
- Best-effort side effects are logged and do not raise (example: workflow start/signal in `src/sps/api/routes/cases.py` uses `logger.warning(..., exc_info=True)` and continues).

## Logging

**Framework:** `logging` standard library

**Patterns:**
- `logger = logging.getLogger(__name__)` per module (example: `src/sps/api/routes/cases.py`).
- Log messages embed key/value pairs in a single string for structured parsing (example: `"cases.requirements_fetch_failed case_id=%s exc_type=%s"` in `src/sps/api/routes/cases.py`).
- Redaction filter applied globally to scrub secrets (see `src/sps/logging/redaction.py`).

## Comments

**When to Comment:**
- Use module/class/function docstrings for intent and constraints (examples: `src/sps/workflows/permit_case/contracts.py`, `src/sps/services/ops_metrics.py`).
- Inline comments for operational constraints or best-effort behavior (example: `# Signal delivery — best-effort` in `src/sps/api/routes/cases.py`).

**JSDoc/TSDoc:**
- Not applicable (Python codebase).

## Function Design

**Size:**
- Decompose route handlers into small, focused helpers for mapping DB rows → response models (examples: `_jurisdiction_row_to_response` and `_submission_attempt_row_to_response` in `src/sps/api/routes/cases.py`).

**Parameters:**
- Use keyword-only arguments for clarity in service helpers (example: `build_ops_metrics_response(db, *, now=None, stalled_review_threshold=None)` in `src/sps/services/ops_metrics.py`).

**Return Values:**
- Explicit return type hints for public APIs and helpers (examples: `healthz() -> dict[str, str]` in `src/sps/api/main.py`, `redacted_postgres_dsn() -> str` in `src/sps/config.py`).

## Module Design

**Exports:**
- Modules expose classes and functions directly; `__init__.py` files are minimal and do not re-export (example: `src/sps/services/__init__.py`).

**Barrel Files:**
- Not used; package-level `__init__.py` contains only docstrings (example: `src/sps/services/__init__.py`).

---

*Convention analysis: 2026-03-17*
