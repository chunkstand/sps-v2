from __future__ import annotations

import logging
from enum import StrEnum
from typing import Callable, Iterable

from fastapi import Depends, Header, HTTPException, Request

from sps.auth.identity import AuthError, Identity, validate_jwt_identity
from sps.config import get_settings

logger = logging.getLogger(__name__)


class Role(StrEnum):
    INTAKE = "intake"
    REVIEWER = "reviewer"
    OPS = "ops"
    RELEASE = "release"
    ESCALATION_OWNER = "escalation-owner"
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


def _identity_for_reviewer_api_key(api_key: str | None) -> Identity | None:
    if api_key is None:
        return None

    settings = get_settings()
    if api_key != settings.reviewer_api_key:
        _emit_denied_log(
            error_code="invalid_api_key",
            subject=None,
            roles=None,
            auth_reason="invalid_api_key",
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key"},
        )

    return Identity(
        subject="reviewer-api-key",
        roles=(Role.REVIEWER.value, Role.OPS.value, Role.RELEASE.value),
        issuer=None,
        audience=None,
    )


def require_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Identity:
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


def require_service_principal(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_reviewer_api_key: str | None = Header(default=None, alias="X-Reviewer-Api-Key"),
) -> Identity:
    api_identity = _identity_for_reviewer_api_key(x_reviewer_api_key)
    if api_identity is not None:
        logger.info("auth.legacy_reviewer_api_key_used guard=service_principal")
        return api_identity

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
            detail={
                "error": "auth_required",
                "auth_reason": "missing_or_invalid_authorization",
                "guard": "service_principal",
            },
        )

    settings = get_settings()
    try:
        identity = validate_jwt_identity(
            token,
            settings,
            expected_principal_type="service_principal",
        )
    except AuthError as exc:
        _emit_denied_log(
            error_code="service_principal_denied",
            subject=None,
            roles=None,
            auth_reason=exc.reason,
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "auth_required",
                "auth_reason": exc.reason,
                "guard": "service_principal",
            },
        ) from exc

    mtls_header_name = settings.auth_mtls_signal_header
    mtls_value = request.headers.get(mtls_header_name)
    if mtls_value is None or not mtls_value.strip():
        _emit_denied_log(
            error_code="mtls_required",
            subject=identity.subject,
            roles=identity.roles,
            auth_reason="missing_mtls_signal",
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "auth_required",
                "auth_reason": "missing_mtls_signal",
                "guard": "mtls_signal",
            },
        )

    return identity


def _normalize_roles(roles: Iterable[str]) -> set[str]:
    return {role.lower() for role in roles}


def require_roles_for(guard: Callable[..., Identity], *required: Role):
    required_values = tuple(role.value for role in required)

    def _dependency(identity: Identity = Depends(guard)) -> Identity:
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


def require_roles(*required: Role):
    return require_roles_for(require_identity, *required)


def require_reviewer_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_reviewer_api_key: str | None = Header(default=None, alias="X-Reviewer-Api-Key"),
) -> Identity:
    api_identity = _identity_for_reviewer_api_key(x_reviewer_api_key)
    if api_identity is not None:
        return api_identity

    if not authorization:
        _emit_denied_log(
            error_code="missing_api_key",
            subject=None,
            roles=None,
            auth_reason="missing_api_key",
        )
        raise HTTPException(status_code=401, detail={"error": "missing_api_key"})

    identity = require_identity(authorization)
    identity_roles = _normalize_roles(identity.roles)
    if Role.ADMIN.value in identity_roles or Role.REVIEWER.value in identity_roles:
        return identity

    _emit_denied_log(
        error_code="role_denied",
        subject=identity.subject,
        roles=identity.roles,
        required_roles=(Role.REVIEWER.value,),
    )
    raise HTTPException(
        status_code=403,
        detail={"error_code": "role_denied", "required_roles": [Role.REVIEWER.value]},
    )
