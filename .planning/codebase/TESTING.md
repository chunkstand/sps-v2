# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

**Runner:**
- pytest >= 8 (declared in `pyproject.toml`).
- Config: `pyproject.toml` (`[tool.pytest.ini_options]` with `fixtures`, `integration`, `unit` markers).

**Assertion Library:**
- pytest built-in assertions.

**Run Commands:**
```bash
pytest
pytest -q
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py
```

## Test File Organization

**Location:**
- Centralized under `tests/` with helpers and fixtures subfolders: `tests/helpers/`, `tests/fixtures/`.

**Naming:**
- Scenario-driven names: `tests/m004_s01_intake_api_workflow_test.py`, `tests/m010_s01_auth_rbac_test.py`.
- Sequence-style names for baseline checks: `tests/s01_db_schema_test.py`.

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
def test_intake_flow_reaches_intake_complete() -> None:
    asyncio.run(_run_intake_flow())

async def _run_intake_flow() -> None:
    _require_temporal_integration()
    _wait_for_postgres_ready()
    _migrate_db()
    ...
```
Pattern from `tests/m004_s01_intake_api_workflow_test.py`.

**Patterns:**
- Helper functions for setup/teardown live in each test module: `_reset_db()` in `tests/m004_s01_intake_api_workflow_test.py`.
- Integration tests are opt-in with `pytest.skip` when `SPS_RUN_TEMPORAL_INTEGRATION` is not set: `tests/m002_s01_temporal_permit_case_workflow_test.py`, `tests/m009_s01_dashboard_test.py`.
- Async tests use `@pytest.mark.anyio` with `httpx.AsyncClient`: `tests/m009_s01_dashboard_test.py`.

## Mocking

**Framework:** pytest `monkeypatch`

**Patterns:**
```python
@pytest.fixture()
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_ISSUER", "test-issuer")
    ...
```
Pattern from `tests/m010_s01_auth_rbac_test.py`.

**What to Mock:**
- Environment variables and config for auth or runtime flags: `tests/m010_s01_auth_rbac_test.py`.

**What NOT to Mock:**
- Database and Temporal behavior in integration tests; they use live Postgres/Temporal when enabled: `tests/m004_s01_intake_api_workflow_test.py`, `tests/m002_s01_temporal_permit_case_workflow_test.py`.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def seed_fixtures(db_session: Session):
    def _seed(case_id: str, submission_attempt_id: str, attempt_number: int = 1, status: str = "SUBMITTED"):
        return seed_submission_attempt(db_session, case_id, submission_attempt_id, attempt_number, status)
    return _seed
```
Pattern from `tests/conftest.py` using `tests/fixtures/seed_submission_package.py`.

**Location:**
- Shared fixtures in `tests/fixtures/` and helper utilities in `tests/helpers/`.

## Coverage

**Requirements:** Not detected

**View Coverage:**
```bash
# Not detected
```

## Test Types

**Unit Tests:**
- API auth/permission checks and helpers without external services: `tests/m010_s01_auth_rbac_test.py`.

**Integration Tests:**
- FastAPI + Postgres + Temporal flows with env-gated execution: `tests/m004_s01_intake_api_workflow_test.py`, `tests/m002_s01_temporal_permit_case_workflow_test.py`.

**E2E Tests:**
- Not used

## Common Patterns

**Async Testing:**
```python
@pytest.mark.anyio
async def test_ops_dashboard_page_renders() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ops")
```
Pattern from `tests/m009_s01_dashboard_test.py`.

**Error Testing:**
```python
with pytest.raises(asyncio.TimeoutError):
    await asyncio.wait_for(handle.result(), timeout=1.0)
```
Pattern from `tests/m002_s01_temporal_permit_case_workflow_test.py`.

---

*Testing analysis: 2026-03-17*
