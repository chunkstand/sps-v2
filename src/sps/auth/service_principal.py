from __future__ import annotations

import datetime as dt
from typing import Iterable

import jwt

from sps.config import Settings, get_settings


def mint_service_principal_jwt(
    *,
    subject: str,
    roles: Iterable[str],
    settings: Settings | None = None,
    expires_in: dt.timedelta | None = None,
) -> str:
    active_settings = settings or get_settings()
    now = dt.datetime.now(tz=dt.UTC)
    payload = {
        "sub": subject,
        "roles": list(roles),
        "iss": active_settings.auth_jwt_issuer,
        "aud": active_settings.auth_jwt_audience,
        "iat": now,
        "exp": now + (expires_in or dt.timedelta(minutes=10)),
        "principal_type": "service_principal",
    }
    return jwt.encode(
        payload,
        active_settings.auth_jwt_secret,
        algorithm=active_settings.auth_jwt_algorithm,
    )


def build_service_principal_headers(
    *,
    roles: Iterable[str],
    subject: str = "svc-demo",
    bearer_token: str | None = None,
    mtls_header_name: str | None = None,
    mtls_header_value: str = "cert-present",
    settings: Settings | None = None,
) -> dict[str, str]:
    active_settings = settings or get_settings()
    token = bearer_token or mint_service_principal_jwt(
        subject=subject,
        roles=roles,
        settings=active_settings,
    )
    headers = {"Authorization": f"Bearer {token}"}
    header_name = mtls_header_name or active_settings.auth_mtls_signal_header
    if mtls_header_value.strip():
        headers[header_name] = mtls_header_value
    return headers
