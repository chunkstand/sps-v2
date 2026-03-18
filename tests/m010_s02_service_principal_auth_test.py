from __future__ import annotations

import logging

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from sps.api.main import app
from sps.config import get_settings
from tests.helpers.auth_tokens import build_jwt, build_service_principal_jwt

pytestmark = pytest.mark.integration


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


def _auth_headers(
    token: str,
    *,
    mtls_header_value: str | None = None,
    mtls_header_name: str | None = None,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if mtls_header_value is not None:
        settings = get_settings()
        header_name = mtls_header_name or settings.auth_mtls_signal_header
        headers[header_name] = mtls_header_value
    return headers


def test_service_principal_allows_with_mtls_header(auth_env: None) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-ops", roles=["ops"])
    response = client.get(
        "/api/v1/ops/dashboard/metrics",
        headers=_auth_headers(token, mtls_header_value="cert-present"),
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    ("method", "path", "roles", "payload", "expected"),
    [
        ("get", "/api/v1/ops/dashboard/metrics", ["ops"], None, 200),
        ("get", "/api/v1/ops/release-blockers", ["ops"], None, 200),
        ("post", "/api/v1/releases/bundles", ["release"], {}, 422),
    ],
)
def test_service_principal_access_matrix_with_mtls(
    auth_env: None,
    method: str,
    path: str,
    roles: list[str],
    payload: dict[str, object] | None,
    expected: int,
) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-principal", roles=roles)
    response = client.request(
        method,
        path,
        json=payload,
        headers=_auth_headers(token, mtls_header_value="cert-present"),
    )
    assert response.status_code == expected, response.text


def test_service_principal_missing_principal_type(auth_env: None) -> None:
    client = TestClient(app)
    token = build_jwt(subject="svc-ops", roles=["ops"])
    response = client.get(
        "/api/v1/ops/dashboard/metrics",
        headers=_auth_headers(token, mtls_header_value="cert-present"),
    )
    assert response.status_code == 401
    payload = response.json()["detail"]
    assert payload["error"] == "auth_required"
    assert payload["auth_reason"] == "missing_principal_type"
    assert payload["guard"] == "service_principal"
    assert token not in response.text


def test_service_principal_invalid_principal_type(auth_env: None) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(
        subject="svc-ops",
        roles=["ops"],
        principal_type="human",
    )
    response = client.get(
        "/api/v1/ops/dashboard/metrics",
        headers=_auth_headers(token, mtls_header_value="cert-present"),
    )
    assert response.status_code == 401
    payload = response.json()["detail"]
    assert payload["error"] == "auth_required"
    assert payload["auth_reason"] == "invalid_principal_type"
    assert payload["guard"] == "service_principal"
    assert token not in response.text


def test_service_principal_missing_mtls_header(
    auth_env: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-ops", roles=["ops"])
    logger = logging.getLogger("sps.auth.rbac")
    logger.disabled = False
    logger.propagate = True
    logger.setLevel(logging.WARNING)

    with caplog.at_level(logging.WARNING):
        response = client.get("/api/v1/ops/dashboard/metrics", headers=_auth_headers(token))

    assert response.status_code == 401
    payload = response.json()["detail"]
    assert payload["error"] == "auth_required"
    assert payload["auth_reason"] == "missing_mtls_signal"
    assert payload["guard"] == "mtls_signal"
    assert token not in response.text

    matching = [
        record
        for record in caplog.records
        if record.name == "sps.auth.rbac" and "api.auth.denied" in record.message
    ]
    assert matching
    assert "missing_mtls_signal" in matching[0].message


@pytest.mark.parametrize(
    ("method", "path", "roles", "payload"),
    [
        ("get", "/api/v1/ops/dashboard/metrics", ["ops"], None),
        ("get", "/api/v1/ops/release-blockers", ["ops"], None),
        ("post", "/api/v1/releases/bundles", ["release"], {}),
    ],
)
def test_service_principal_requires_mtls_for_protected_routes(
    auth_env: None,
    method: str,
    path: str,
    roles: list[str],
    payload: dict[str, object] | None,
) -> None:
    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-principal", roles=roles)
    response = client.request(method, path, json=payload, headers=_auth_headers(token))
    assert response.status_code == 401
    payload_json = response.json()["detail"]
    assert payload_json["error"] == "auth_required"
    assert payload_json["auth_reason"] == "missing_mtls_signal"


def test_service_principal_honors_mtls_header_setting(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPS_AUTH_MTLS_SIGNAL_HEADER", "X-Test-MTLS")
    get_settings.cache_clear()

    client = TestClient(app)
    token = build_service_principal_jwt(subject="svc-ops", roles=["ops"])
    response = client.get(
        "/api/v1/ops/dashboard/metrics",
        headers=_auth_headers(token, mtls_header_value="cert", mtls_header_name="X-Test-MTLS"),
    )
    assert response.status_code == 200, response.text
