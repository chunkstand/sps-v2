from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

import jwt

from sps.auth.service_principal import build_service_principal_headers as _build_sp_headers
from sps.auth.service_principal import mint_service_principal_jwt as _mint_sp_jwt
from sps.config import get_settings


def build_jwt(
    *,
    subject: str,
    roles: Iterable[str] | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    secret: str | None = None,
    algorithm: str | None = None,
    expires_in: dt.timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = dt.datetime.now(tz=dt.UTC)

    payload = {
        "sub": subject,
        "roles": list(roles or []),
        "iss": issuer or settings.auth_jwt_issuer,
        "aud": audience or settings.auth_jwt_audience,
        "iat": now,
        "exp": now + (expires_in or dt.timedelta(minutes=10)),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        secret or settings.auth_jwt_secret,
        algorithm=algorithm or settings.auth_jwt_algorithm,
    )


def build_service_principal_jwt(
    *,
    subject: str,
    roles: Iterable[str] | None = None,
    principal_type: str = "service_principal",
    issuer: str | None = None,
    audience: str | None = None,
    secret: str | None = None,
    algorithm: str | None = None,
    expires_in: dt.timedelta | None = None,
) -> str:
    if (
        principal_type == "service_principal"
        and issuer is None
        and audience is None
        and secret is None
        and algorithm is None
    ):
        return _mint_sp_jwt(
            subject=subject,
            roles=roles or (),
            expires_in=expires_in,
        )
    return build_jwt(
        subject=subject,
        roles=roles,
        issuer=issuer,
        audience=audience,
        secret=secret,
        algorithm=algorithm,
        expires_in=expires_in,
        extra_claims={"principal_type": principal_type},
    )


def build_service_principal_headers(
    *,
    roles: Iterable[str],
    subject: str = "svc-demo",
    mtls_header_value: str = "cert-present",
    bearer_token: str | None = None,
    mtls_header_name: str | None = None,
) -> dict[str, str]:
    return _build_sp_headers(
        roles=roles,
        subject=subject,
        bearer_token=bearer_token,
        mtls_header_name=mtls_header_name,
        mtls_header_value=mtls_header_value,
    )
