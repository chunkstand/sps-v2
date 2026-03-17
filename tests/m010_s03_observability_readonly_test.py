from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from sps.api.main import app
from sps.config import get_settings
from tests.helpers.auth_tokens import build_service_principal_jwt


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("SPS_AUTH_JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SPS_AUTH_JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("SPS_AUTH_MTLS_SIGNAL_HEADER", "X-Forwarded-Client-Cert")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _auth_headers(token: str, *, mtls_header_value: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if mtls_header_value is not None:
        settings = get_settings()
        headers[settings.auth_mtls_signal_header] = mtls_header_value
    return headers


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/ops/dashboard/metrics"),
        ("put", "/api/v1/ops/dashboard/metrics"),
        ("patch", "/api/v1/ops/dashboard/metrics"),
        ("delete", "/api/v1/ops/dashboard/metrics"),
        ("post", "/api/v1/ops/release-blockers"),
        ("put", "/api/v1/ops/release-blockers"),
        ("patch", "/api/v1/ops/release-blockers"),
        ("delete", "/api/v1/ops/release-blockers"),
    ],
)
def test_ops_routes_reject_mutations(auth_env: None, method: str, path: str) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-ops", roles=["ops"])
    response = client.request(
        method,
        path,
        headers=_auth_headers(token, mtls_header_value="present"),
    )
    assert response.status_code == 405, response.text


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("post", "/api/v1/releases/bundles", 403),
        ("put", "/api/v1/releases/bundles", 405),
        ("patch", "/api/v1/releases/bundles", 405),
        ("delete", "/api/v1/releases/bundles", 405),
        ("post", "/api/v1/releases/rollbacks/rehearsals", 403),
        ("put", "/api/v1/releases/rollbacks/rehearsals", 405),
        ("patch", "/api/v1/releases/rollbacks/rehearsals", 405),
        ("delete", "/api/v1/releases/rollbacks/rehearsals", 405),
    ],
)
def test_release_routes_reject_mutations(
    auth_env: None,
    method: str,
    path: str,
    expected: int,
) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-ops", roles=["ops"])
    response = client.request(
        method,
        path,
        headers=_auth_headers(token, mtls_header_value="present"),
    )
    assert response.status_code == expected, response.text
