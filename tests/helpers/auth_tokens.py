from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

import jwt

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
