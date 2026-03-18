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
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _auth_headers(token: str, *, mtls_header_value: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if mtls_header_value is not None:
        settings = get_settings()
        headers[settings.auth_mtls_signal_header] = mtls_header_value
    return headers


def _legacy_key_headers() -> dict[str, str]:
    return {"X-Reviewer-Api-Key": get_settings().reviewer_api_key}


def test_auth_required_missing_token(auth_env: None) -> None:
    client = TestClient(app)
    response = client.get("/api/v1/ops/dashboard/metrics")
    assert response.status_code == 401
    payload = response.json()["detail"]
    assert payload["error"] == "auth_required"
    assert payload["auth_reason"] == "missing_or_invalid_authorization"
    assert "Bearer" not in response.text


def test_auth_required_invalid_token(auth_env: None) -> None:
    client = TestClient(app)
    token = build_jwt(subject="user-1", roles=["ops"], secret="wrong-secret")
    response = client.get("/api/v1/ops/dashboard/metrics", headers=_auth_headers(token))
    assert response.status_code == 401
    payload = response.json()["detail"]
    assert payload["error"] == "auth_required"
    assert payload["auth_reason"] == "invalid_token"
    assert token not in response.text


def test_role_denied(auth_env: None) -> None:
    client = TestClient(app)
    token = build_jwt(subject="user-1", roles=["intake"])
    response = client.get(
        "/api/v1/reviews/queue",
        headers=_auth_headers(token),
    )
    assert response.status_code == 403
    payload = response.json()["detail"]
    assert payload["error_code"] == "role_denied"
    assert "reviewer" in payload["required_roles"]
    assert token not in response.text


@pytest.mark.parametrize(
    ("method", "path", "payload", "expected"),
    [
        ("get", "/api/v1/reviews/queue", None, 200),
        ("get", "/api/v1/ops/dashboard/metrics", None, 200),
        ("get", "/api/v1/ops/release-blockers", None, 200),
        ("post", "/api/v1/releases/bundles", {}, 422),
    ],
)
def test_legacy_reviewer_api_key_access_matrix(
    auth_env: None,
    method: str,
    path: str,
    payload: dict[str, object] | None,
    expected: int,
) -> None:
    client = TestClient(app)
    response = client.request(method, path, json=payload, headers=_legacy_key_headers())
    assert response.status_code == expected, response.text
    assert response.status_code not in (401, 403)


@pytest.mark.parametrize(
    ("method", "path", "roles", "payload", "expected", "service_principal"),
    [
        ("post", "/api/v1/cases", ["intake"], {}, 422, False),
        ("post", "/api/v1/evidence/artifacts", ["intake"], {}, 422, False),
        ("post", "/api/v1/reviews/decisions", ["reviewer"], {}, 422, False),
        ("post", "/api/v1/reviews/decisions", ["admin"], {}, 422, False),
        ("get", "/reviewer", ["reviewer"], None, 200, False),
        ("post", "/api/v1/contradictions", ["reviewer"], {}, 422, False),
        ("get", "/api/v1/dissents/DISSENT-404", ["reviewer"], None, 404, False),
        ("post", "/api/v1/releases/bundles", ["release"], {}, 422, True),
        ("get", "/api/v1/ops/release-blockers", ["ops"], None, 200, True),
        ("get", "/api/v1/ops/dashboard/metrics", ["ops"], None, 200, True),
        ("get", "/ops", ["ops"], None, 200, False),
    ],
)
def test_allowed_role_access(
    auth_env: None,
    method: str,
    path: str,
    roles: list[str],
    payload: dict[str, object] | None,
    expected: int,
    service_principal: bool,
) -> None:
    client = TestClient(app)
    if service_principal:
        token = build_service_principal_jwt(subject="svc-ops", roles=roles)
        headers = _auth_headers(token, mtls_header_value="present")
    else:
        token = build_jwt(subject="user-1", roles=roles)
        headers = _auth_headers(token)
    response = client.request(method, path, json=payload, headers=headers)
    assert response.status_code == expected, response.text
    assert response.status_code not in (401, 403)


def test_denied_log_emitted(auth_env: None, caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(app)
    logger = logging.getLogger("sps.auth.rbac")
    logger.disabled = False
    logger.propagate = True
    logger.setLevel(logging.WARNING)

    with caplog.at_level(logging.WARNING):
        response = client.get("/api/v1/reviews/queue")

    assert response.status_code == 401
    matching = [
        record
        for record in caplog.records
        if record.name == "sps.auth.rbac" and "api.auth.denied" in record.message
    ]
    assert matching
    assert "Bearer" not in caplog.text
