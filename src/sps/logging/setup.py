from __future__ import annotations

import logging

from sps.config import get_settings
from sps.logging.redaction import attach_redaction_filter

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """Configure process-wide logging once and keep redaction installed.

    We rely on the root logger for handler fan-out, but we still install the
    redaction plumbing globally so child loggers and test capture handlers see
    sanitized records even when they are attached after startup.
    """

    settings = get_settings()
    root = logging.getLogger()

    if not root.handlers:
        logging.basicConfig(
            level=settings.log_level.upper(),
            format=_LOG_FORMAT,
        )
    else:
        root.setLevel(settings.log_level.upper())

    attach_redaction_filter(root)
