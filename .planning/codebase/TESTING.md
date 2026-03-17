# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

**Runner:**
- pytest >= 8 (declared in `pyproject.toml`)
- Config: `pyproject.toml` (`[tool.pytest.ini_options]` with `fixtures` and `integration` markers)

**Assertion Library:**
- pytest built-in assertions

**Run Commands:**
```bash
pytest
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py
# Watch mode: Not detected
# Coverage: Not detected
```

## Test File Organization

**Location:**
- Centralized under `tests/` with helpers and fixtures subfolders (`tests/helpers/`, `tests/fixtures/`).

**Naming:**
- Scenario-driven names: `tests/m004_s01_intake_api_workflow_test.py`, `tests/m012_s01_override_guard_unit_test.py`.
- Sequence-style smoke tests: `tests/s01_db_schema_test.py`.

**Structure:**
```
tests/
├── conftest.py
├── helpers/
├── fixtures/
└── m###_s##_..._test.py
```

## Test Structure

**Suite Organization:**
```python
def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    ...

def test_ops_metrics_endpoint_returns_expected_counts() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()
    ...
```
Pattern shown in `tests/m009_s01_dashboard_test.py`.

**Patterns:**
- Helper functions for setup/teardown live in each test module (example: `_reset_db()` in `tests/m004_s01_intake_api_workflow_test.py`).
- Environment-gated integration tests using `pytest.skip` at module import when `SPS_RUN_TEMPORAL_INTEGRATION` is not set (example: `tests/m009_s01_dashboard_test.py`).
- Async tests use `@pytest.mark.anyio` with `async def` (example: `tests/m009_s01_dashboard_test.py`).

## Mocking

**Framework:** pytest `monkeypatch`

**Patterns:**
```python
@pytest.mark.usefixtures("monkeypatch")
def test_fixture_override_rewrites_case_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV, fixture_case_id)
```
Pattern shown in `tests/m004_s03_fixture_override_test.py`.

**What to Mock:**
- Environment variables and runtime flags via `monkeypatch` (example: `tests/m004_s03_fixture_override_test.py`).

**What NOT to Mock:**
- Database and Temporal behavior in integration tests; tests prefer real Postgres/Temporal when enabled (examples: `tests/m004_s01_intake_api_workflow_test.py`, `tests/m012_s01_override_guard_unit_test.py`).

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def seed_fixtures(db_session: Session):
    def _seed(case_id: str, submission_attempt_id: str, attempt_number: int = 1, status: str = "SUBMITTED"):
        return seed_submission_attempt(db_session, case_id, submission_attempt_id, attempt_number, status)
    return _seed
```
Pattern shown in `tests/conftest.py` using `tests/fixtures/seed_submission_package.py`.

**Location:**
- Shared fixtures in `tests/fixtures/` and module-level helpers in individual test files.

## Coverage

**Requirements:** Not detected

**View Coverage:**
```bash
# Not detected
```

## Test Types

**Unit Tests:**
- Guard and contract logic that runs with Postgres but without Temporal workers (example: `tests/m012_s01_override_guard_unit_test.py`).

**Integration Tests:**
- Full API/DB/Temporal workflows with opt-in env gating (examples: `tests/m004_s01_intake_api_workflow_test.py`, `tests/m009_s01_dashboard_test.py`).

**E2E Tests:**
- Not used

## Common Patterns

**Async Testing:**
```python
@pytest.mark.anyio
async def test_ops_dashboard_page_renders() -> None:
    ...
```
Pattern shown in `tests/m009_s01_dashboard_test.py`.

**Error Testing:**
```python
with pytest.raises(IntegrityError):
    db_session.commit()
```
Pattern shown in `tests/s01_db_schema_test.py`.

---

*Testing analysis: 2026-03-17*
