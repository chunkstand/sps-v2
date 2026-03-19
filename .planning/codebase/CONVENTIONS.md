# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

**Files:**
- Use `snake_case.py` for modules: `src/sps/api/routes/cases.py`, `src/sps/services/release_bundle_manifest.py`, `tests/m004_s01_intake_api_workflow_test.py`.
- Tests end with `_test.py` and include milestone-style prefixes: `tests/m010_s01_auth_rbac_test.py`, `tests/s01_db_schema_test.py`.

**Functions:**
- Use `snake_case` for functions and methods: `src/sps/config.py`, `src/sps/api/routes/cases.py`.
- Private helpers use a leading underscore: `_new_case_id` in `src/sps/api/routes/cases.py`, `_run_integration` in `tests/m002_s01_temporal_permit_case_workflow_test.py`.

**Variables:**
- Use `snake_case` for locals and parameters; constants use `UPPER_SNAKE_CASE`: `STATIC_DIR` in `src/sps/api/main.py`.
- Module-private constants often use a leading underscore: `_CASE_ID_PREFIX` in `src/sps/api/routes/cases.py`.

**Types:**
- Classes use `PascalCase`: `PermitCaseWorkflow` in `src/sps/workflows/permit_case/workflow.py`, `AuditEvent` in `src/sps/db/models.py`.
- Dataclasses are used for DTOs: `PackageManifestEntry` in `src/sps/services/release_bundle_manifest.py`.

## Code Style

**Formatting:**
- Tool: Ruff line-length configuration.
- Key settings: `line-length = 100` in `pyproject.toml`.
- Use `from __future__ import annotations` in modules: `src/sps/api/main.py`, `src/sps/config.py`.

**Linting:**
- Tool: Ruff configured via `pyproject.toml`.

## Import Organization

**Order:**
1. Standard library imports
2. Third-party dependencies
3. Local package imports

**Path Aliases:**
- Use absolute package imports from `sps.*` and `tests.*`: `src/sps/api/routes/cases.py`, `tests/m010_s01_auth_rbac_test.py`.

## Error Handling

**Patterns:**
- Catch `SQLAlchemyError` and raise `HTTPException` with structured `detail` payloads: `src/sps/api/routes/cases.py`.
- Preserve exception context with `raise ... from exc`: `src/sps/api/routes/cases.py`, `src/sps/services/release_bundle_manifest.py`.
- Use `RuntimeError` for unexpected workflow or integration failures: `src/sps/workflows/permit_case/workflow.py`, `tests/m002_s01_temporal_permit_case_workflow_test.py`.

## Logging

**Framework:** `logging` standard library

**Patterns:**
- Use `logging.getLogger(__name__)` per module: `src/sps/api/routes/cases.py`, `src/sps/workflows/permit_case/workflow.py`.
- Log structured key/value strings in messages: `src/sps/api/routes/cases.py`, `src/sps/workflows/permit_case/workflow.py`.
- Apply a redaction filter to scrub secrets: `src/sps/logging/redaction.py` and `src/sps/api/main.py`.

## Comments

**When to Comment:**
- Use docstrings for modules and helper functions with non-obvious behavior: `tests/m004_s01_intake_api_workflow_test.py`, `tests/helpers/temporal_replay.py`.
- Inline comments explain constraints or best-effort behavior: `src/sps/workflows/permit_case/workflow.py`, `src/sps/api/routes/cases.py`.
- Use `# pragma: no cover` for infra-dependent branches in tests: `tests/m002_s01_temporal_permit_case_workflow_test.py`.

**JSDoc/TSDoc:**
- Not applicable (Python codebase).

## Function Design

**Size:** Prefer small helpers for mapping or orchestration logic: `_jurisdiction_row_to_response` in `src/sps/api/routes/cases.py`.

**Parameters:**
- Type-annotate parameters and return values: `src/sps/config.py`, `tests/helpers/auth_tokens.py`.
- Use keyword-only arguments for clarity in helpers: `src/sps/services/release_bundle_manifest.py`, `tests/helpers/temporal_replay.py`.

**Return Values:**
- Return typed Pydantic models or dataclasses: `src/sps/services/release_bundle_manifest.py`, `src/sps/api/routes/cases.py`.

## Module Design

**Exports:**
- Modules expose routers or service entry points; helpers remain private via leading underscore: `src/sps/api/routes/cases.py`.

**Barrel Files:**
- Package `__init__.py` files exist but avoid heavy re-exports: `src/sps/api/__init__.py`, `src/sps/services/__init__.py`.

---

*Convention analysis: 2026-03-17*
