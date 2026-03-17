from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, PyJWTError

from sps.config import Settings


class AuthError(Exception):
    """Raised when JWT validation fails for a known reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Identity:
    subject: str
    roles: tuple[str, ...]
    issuer: str | None
    audience: str | None


def _coerce_roles(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(role, str) for role in value):
        return tuple(value)
    raise AuthError("invalid_roles")


def validate_jwt_identity(token: str, settings: Settings) -> Identity:
    """Validate and decode the JWT, returning an Identity on success.

    Enforces issuer, audience, expiry, and subject presence. Never logs tokens.
    """

    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm],
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except ExpiredSignatureError as exc:
        raise AuthError("token_expired") from exc
    except InvalidAudienceError as exc:
        raise AuthError("invalid_audience") from exc
    except InvalidIssuerError as exc:
        raise AuthError("invalid_issuer") from exc
    except PyJWTError as exc:
        raise AuthError("invalid_token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthError("missing_subject")

    roles = _coerce_roles(payload.get("roles"))

    issuer = payload.get("iss") if isinstance(payload.get("iss"), str) else None
    audience = payload.get("aud") if isinstance(payload.get("aud"), str) else None

    return Identity(subject=subject, roles=roles, issuer=issuer, audience=audience)
