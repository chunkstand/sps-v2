from __future__ import annotations

import logging
from enum import StrEnum
from typing import Iterable

from fastapi import Depends, Header, HTTPException

from sps.auth.identity import AuthError, Identity, validate_jwt_identity
from sps.config import get_settings

logger = logging.getLogger(__name__)


class Role(StrEnum):
    INTAKE = "intake"
    REVIEWER = "reviewer"
    OPS = "ops"
    RELEASE = "release"
    ADMIN = "admin"


def _emit_denied_log(
    *,
    error_code: str,
    subject: str | None,
    roles: Iterable[str] | None,
    required_roles: Iterable[str] | None = None,
    auth_reason: str | None = None,
) -> None:
    logger.warning(
        "api.auth.denied error_code=%s subject=%s roles=%s required_roles=%s auth_reason=%s",
        error_code,
        subject,
        list(roles) if roles is not None else None,
        list(required_roles) if required_roles is not None else None,
        auth_reason,
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    return token


def require_identity(authorization: str | None = Header(default=None, alias="Authorization")) -> Identity:
    token = _extract_bearer_token(authorization)
    if token is None:
        _emit_denied_log(
            error_code="auth_required",
            subject=None,
            roles=None,
            auth_reason="missing_or_invalid_authorization",
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "auth_required", "auth_reason": "missing_or_invalid_authorization"},
        )

    settings = get_settings()
    try:
        identity = validate_jwt_identity(token, settings)
    except AuthError as exc:
        _emit_denied_log(
            error_code="auth_invalid",
            subject=None,
            roles=None,
            auth_reason=exc.reason,
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "auth_required", "auth_reason": exc.reason},
        ) from exc

    return identity


def _normalize_roles(roles: Iterable[str]) -> set[str]:
    return {role.lower() for role in roles}


def require_roles(*required: Role):
    required_values = tuple(role.value for role in required)

    def _dependency(identity: Identity = Depends(require_identity)) -> Identity:
        identity_roles = _normalize_roles(identity.roles)
        if Role.ADMIN.value in identity_roles:
            return identity

        if not identity_roles.intersection(required_values):
            _emit_denied_log(
                error_code="role_denied",
                subject=identity.subject,
                roles=identity.roles,
                required_roles=required_values,
            )
            raise HTTPException(
                status_code=403,
                detail={"error_code": "role_denied", "required_roles": list(required_values)},
            )
        return identity

    return _dependency
