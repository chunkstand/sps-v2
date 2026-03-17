from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

from sps.config import _redact_url_password

REDACTION_TOKEN = "[REDACTED]"

_SECRET_FIELD_NAMES = {
    "authorization",
    "api_key",
    "reviewer_api_key",
    "jwt_secret",
    "password",
    "secret",
    "token",
    "access_token",
    "dsn",
    "db_dsn",
    "db_password",
}

_BASE_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())

_AUTH_PATTERN = re.compile(r"(?i)(authorization\s*[:=]\s*)(?:Bearer\s+)?([^\s,;]+)")
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(?P<key>api_key|reviewer_api_key|jwt_secret|password|token|access_token|dsn)\b\s*[:=]\s*(?P<value>[^\s,;]+)"
)
_DSN_PATTERN = re.compile(r"(?i)\b(postgres(?:ql)?(?:\+\w+)?://[^\s'\"<>]+)")


def _is_secret_key(key: str) -> bool:
    key_lower = key.lower()
    if key_lower in _SECRET_FIELD_NAMES:
        return True
    return key_lower.endswith(("_secret", "_password", "_token", "_api_key", "_dsn"))


def redact_string(value: str) -> str:
    redacted = _AUTH_PATTERN.sub(r"\1" + REDACTION_TOKEN, value)

    def _replace_key_value(match: re.Match[str]) -> str:
        key = match.group("key")
        return f"{key}={REDACTION_TOKEN}"

    redacted = _KEY_VALUE_PATTERN.sub(_replace_key_value, redacted)

    def _replace_dsn(match: re.Match[str]) -> str:
        return _redact_url_password(match.group(1))

    redacted = _DSN_PATTERN.sub(_replace_dsn, redacted)
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, Mapping):
        return {k: (REDACTION_TOKEN if _is_secret_key(str(k)) else redact_value(v)) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [redact_value(v) for v in value]
    return value


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_string(record.getMessage())
        record.args = ()

        for key, value in list(record.__dict__.items()):
            if key in _BASE_RECORD_ATTRS:
                continue
            if _is_secret_key(str(key)):
                record.__dict__[key] = REDACTION_TOKEN
            else:
                record.__dict__[key] = redact_value(value)
        return True


def attach_redaction_filter(logger: logging.Logger | None = None) -> None:
    target = logger or logging.getLogger()

    filter_instance = next((f for f in target.filters if isinstance(f, RedactionFilter)), None)
    if filter_instance is None:
        filter_instance = RedactionFilter()
        target.addFilter(filter_instance)

    for handler in target.handlers:
        if any(isinstance(f, RedactionFilter) for f in handler.filters):
            continue
        handler.addFilter(filter_instance)
