from __future__ import annotations

import logging

from sps.logging.redaction import REDACTION_TOKEN, attach_redaction_filter


logger = logging.getLogger("sps.tests.redaction")


def _prepare(caplog) -> None:
    logger.disabled = False
    logger.propagate = True
    logger.setLevel(logging.INFO)
    caplog.set_level(logging.INFO, logger=logger.name)
    attach_redaction_filter()


def test_redaction_scrubs_message_and_args(caplog) -> None:
    _prepare(caplog)

    secret = "Bearer super-secret-token"
    logger.info("Authorization: %s", secret)

    assert REDACTION_TOKEN in caplog.text
    assert "super-secret-token" not in caplog.text


def test_redaction_scrubs_extra_fields(caplog) -> None:
    _prepare(caplog)

    logger.info(
        "payload",
        extra={
            "authorization": "Bearer abc123",
            "payload": {"reviewer_api_key": "reviewer-secret"},
        },
    )

    record = caplog.records[-1]
    assert record.authorization == REDACTION_TOKEN
    assert record.payload["reviewer_api_key"] == REDACTION_TOKEN


def test_redaction_scrubs_dsn_password(caplog) -> None:
    _prepare(caplog)

    dsn = "postgresql+psycopg://user:password@localhost:5432/sps"
    logger.info("db_dsn=%s", dsn)

    assert "password" not in caplog.text
    assert "postgresql+psycopg://user:***@localhost:5432/sps" in caplog.text


def test_redaction_failure_surface(caplog) -> None:
    _prepare(caplog)

    logger.warning("jwt_secret=top-secret")

    assert REDACTION_TOKEN in caplog.text
    assert "top-secret" not in caplog.text
