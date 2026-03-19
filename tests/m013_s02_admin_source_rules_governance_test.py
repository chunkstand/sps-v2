"""M013 / S02 integration test: admin source rules governance workflow.

Proves intent → review → apply with RBAC enforcement and audit trail persistence.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: API integration test against real Postgres.

## Observability Impact

Signals documented by these tests:
  - audit_events action=ADMIN_SOURCE_RULE_INTENT_CREATED
  - audit_events action=ADMIN_SOURCE_RULE_REVIEW_RECORDED
  - audit_events action=ADMIN_SOURCE_RULE_APPLIED

Diagnostic inspection:
  - SELECT * FROM admin_source_rule_intents;
  - SELECT * FROM admin_source_rule_reviews;
  - SELECT * FROM source_rules;
  - SELECT action, correlation_id FROM audit_events WHERE correlation_id = <intent_id>;

Failure state visibility:
  - apply before approval → HTTP 409 review_required (no apply audit event)
  - wrong role → HTTP 403 role_denied
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import AuditEvent, SourceRule
from sps.db.session import get_engine, get_sessionmaker
from tests.helpers.auth_tokens import build_jwt

pytestmark = pytest.mark.integration

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    import time

    deadline = time.time() + timeout_s
    engine = get_engine()

    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            import time

            time.sleep(0.5)

    raise RuntimeError(
        f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "heads")


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE admin_source_rule_reviews, "
                "admin_source_rule_intents, source_rules, audit_events CASCADE"
            )
        )


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _db_lifecycle() -> None:  # type: ignore[return]
    _wait_for_postgres_ready()
    _migrate_db()
    yield
    _reset_db()


@pytest.fixture()
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("SPS_AUTH_JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET", "test-secret-0123456789abcdef0123456789")
    monkeypatch.setenv("SPS_AUTH_JWT_ALGORITHM", "HS256")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_admin_source_rules_happy_path(auth_env: None) -> None:
    asyncio.run(_run_admin_source_rules_happy_path())


def test_admin_source_rules_review_required_error_code(auth_env: None) -> None:
    asyncio.run(_run_admin_source_rules_review_required_error_code())


def test_admin_source_rules_role_denied_reviewer_cannot_apply(auth_env: None) -> None:
    asyncio.run(_run_admin_source_rules_rbac_reviewer_cannot_apply())


def test_admin_source_rules_role_denied_admin_cannot_review(auth_env: None) -> None:
    asyncio.run(_run_admin_source_rules_rbac_admin_cannot_review())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_admin_source_rules_happy_path() -> None:
    intent_id = "INTENT-SR-001"
    review_id = "REVIEW-SR-001"
    rule_scope = "REQUIREMENTS_RANKING"
    rule_payload = {"priority": ["utility", "state", "county"]}

    admin_token = build_jwt(subject="admin-user-1", roles=["admin"])
    reviewer_token = build_jwt(subject="reviewer-user-1", roles=["reviewer"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        intent_response = await client.post(
            "/api/v1/admin/source-rules/intents",
            headers=_auth_headers(admin_token),
            json={
                "intent_id": intent_id,
                "rule_scope": rule_scope,
                "rule_payload": rule_payload,
                "requested_by": "admin-user-1",
            },
        )

        assert intent_response.status_code == 201, intent_response.text

        review_response = await client.post(
            "/api/v1/admin/source-rules/reviews",
            headers=_auth_headers(reviewer_token),
            json={
                "review_id": review_id,
                "intent_id": intent_id,
                "reviewer_id": "reviewer-user-1",
                "decision_outcome": "APPROVED",
                "review_payload": {"notes": "approved"},
                "idempotency_key": "IDEMPOTENCY-SR-001",
            },
        )

        assert review_response.status_code == 201, review_response.text

        apply_response = await client.post(
            f"/api/v1/admin/source-rules/apply/{intent_id}",
            headers=_auth_headers(admin_token),
        )

        assert apply_response.status_code == 200, apply_response.text
        apply_body = apply_response.json()
        assert apply_body["intent_id"] == intent_id
        assert apply_body["rule_scope"] == rule_scope

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        source_rule = (
            session.query(SourceRule)
            .filter(SourceRule.rule_scope == rule_scope)
            .one_or_none()
        )
        assert source_rule is not None
        assert source_rule.rule_scope == rule_scope
        assert source_rule.rule_payload == rule_payload

        audit_events = (
            session.query(AuditEvent)
            .filter(AuditEvent.correlation_id == intent_id)
            .all()
        )
        actions = {event.action for event in audit_events}
        assert actions == {
            "ADMIN_SOURCE_RULE_INTENT_CREATED",
            "ADMIN_SOURCE_RULE_REVIEW_RECORDED",
            "ADMIN_SOURCE_RULE_APPLIED",
        }

        audit_by_action = {event.action: event for event in audit_events}
        assert audit_by_action["ADMIN_SOURCE_RULE_INTENT_CREATED"].payload == {
            "intent_id": intent_id
        }
        review_payload = audit_by_action["ADMIN_SOURCE_RULE_REVIEW_RECORDED"].payload
        assert review_payload is not None
        assert review_payload["intent_id"] == intent_id
        assert review_payload["review_id"] == review_id
        assert review_payload["decision_outcome"] == "APPROVED"

        apply_payload = audit_by_action["ADMIN_SOURCE_RULE_APPLIED"].payload
        assert apply_payload is not None
        assert apply_payload["intent_id"] == intent_id
        assert apply_payload["review_id"] == review_id
        assert apply_payload["source_rule_id"] == apply_body["source_rule_id"]


async def _run_admin_source_rules_review_required_error_code() -> None:
    intent_id = "INTENT-SR-002"

    admin_token = build_jwt(subject="admin-user-2", roles=["admin"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        intent_response = await client.post(
            "/api/v1/admin/source-rules/intents",
            headers=_auth_headers(admin_token),
            json={
                "intent_id": intent_id,
                "rule_scope": "PORTAL_MATCHING",
                "rule_payload": {"matching": "strict"},
                "requested_by": "admin-user-2",
            },
        )
        assert intent_response.status_code == 201, intent_response.text

        apply_response = await client.post(
            f"/api/v1/admin/source-rules/apply/{intent_id}",
            headers=_auth_headers(admin_token),
        )

        assert apply_response.status_code == 409, apply_response.text
        body = apply_response.json()
        assert body["detail"]["error_code"] == "review_required"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        apply_events = (
            session.query(AuditEvent)
            .filter(
                AuditEvent.correlation_id == intent_id,
                AuditEvent.action == "ADMIN_SOURCE_RULE_APPLIED",
            )
            .all()
        )
        assert apply_events == []


async def _run_admin_source_rules_rbac_reviewer_cannot_apply() -> None:
    intent_id = "INTENT-SR-003"
    review_id = "REVIEW-SR-003"

    admin_token = build_jwt(subject="admin-user-3", roles=["admin"])
    reviewer_token = build_jwt(subject="reviewer-user-3", roles=["reviewer"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        intent_response = await client.post(
            "/api/v1/admin/source-rules/intents",
            headers=_auth_headers(admin_token),
            json={
                "intent_id": intent_id,
                "rule_scope": "CITATION_REQUIREMENTS",
                "rule_payload": {"citations": ["official", "verified"]},
                "requested_by": "admin-user-3",
            },
        )
        assert intent_response.status_code == 201, intent_response.text

        review_response = await client.post(
            "/api/v1/admin/source-rules/reviews",
            headers=_auth_headers(reviewer_token),
            json={
                "review_id": review_id,
                "intent_id": intent_id,
                "reviewer_id": "reviewer-user-3",
                "decision_outcome": "APPROVED",
                "review_payload": {"notes": "ok"},
                "idempotency_key": "IDEMPOTENCY-SR-003",
            },
        )
        assert review_response.status_code == 201, review_response.text

        apply_response = await client.post(
            f"/api/v1/admin/source-rules/apply/{intent_id}",
            headers=_auth_headers(reviewer_token),
        )
        assert apply_response.status_code == 403
        body = apply_response.json()
        assert body["detail"]["error_code"] == "role_denied"
        assert "admin" in body["detail"]["required_roles"]

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        apply_events = (
            session.query(AuditEvent)
            .filter(
                AuditEvent.correlation_id == intent_id,
                AuditEvent.action == "ADMIN_SOURCE_RULE_APPLIED",
            )
            .all()
        )
        assert apply_events == []


async def _run_admin_source_rules_rbac_admin_cannot_review() -> None:
    intent_id = "INTENT-SR-004"

    admin_token = build_jwt(subject="admin-user-4", roles=["admin"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        intent_response = await client.post(
            "/api/v1/admin/source-rules/intents",
            headers=_auth_headers(admin_token),
            json={
                "intent_id": intent_id,
                "rule_scope": "SOURCE_FRESHNESS",
                "rule_payload": {"max_age_days": 120},
                "requested_by": "admin-user-4",
            },
        )
        assert intent_response.status_code == 201, intent_response.text

        review_response = await client.post(
            "/api/v1/admin/source-rules/reviews",
            headers=_auth_headers(admin_token),
            json={
                "review_id": "REVIEW-SR-004",
                "intent_id": intent_id,
                "reviewer_id": "admin-user-4",
                "decision_outcome": "APPROVED",
                "review_payload": {"notes": "attempt"},
                "idempotency_key": "IDEMPOTENCY-SR-004",
            },
        )

        assert review_response.status_code == 403
        body = review_response.json()
        assert body["detail"]["error_code"] == "role_denied"
        assert "reviewer" in body["detail"]["required_roles"]

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        review_events = (
            session.query(AuditEvent)
            .filter(
                AuditEvent.correlation_id == intent_id,
                AuditEvent.action == "ADMIN_SOURCE_RULE_REVIEW_RECORDED",
            )
            .all()
        )
        assert review_events == []
