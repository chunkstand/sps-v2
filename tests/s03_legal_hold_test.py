from __future__ import annotations

import datetime as dt

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sps.api.main import app
from sps.db.models import EvidenceArtifact, LegalHold, LegalHoldBinding
from sps.db.session import get_engine, get_sessionmaker
from sps.retention.purge import dry_run_purge


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def db_session() -> Session:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(sa.text("TRUNCATE TABLE legal_hold_bindings, legal_holds, evidence_artifacts CASCADE"))

    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_can_insert_and_read_legal_hold_bound_to_artifact(db_session: Session):
    artifact_id = "ART-01KKSMAP4MH6HWGM2RR9J22K79"  # any valid-looking ART-* id

    db_session.add(
        EvidenceArtifact(
            artifact_id=artifact_id,
            artifact_class="REQUIREMENT_EVIDENCE",
            producing_service="pytest",
            linked_case_id=None,
            linked_object_id=None,
            authoritativeness="authoritative",
            retention_class="CASE_CORE_7Y",
            checksum="sha256:" + ("0" * 64),
            storage_uri=f"s3://sps-evidence/evidence/01/{artifact_id}",
            content_bytes=None,
            content_type=None,
            provenance={"producer": "pytest"},
            created_at=_utcnow(),
            expires_at=None,
            legal_hold_flag=False,
        )
    )

    hold = LegalHold(
        hold_id="HOLD-001",
        reason="litigation hold",
        requested_by="Compliance Counsel",
        authorized_by="General Counsel",
        status="ACTIVE",
        released_at=None,
    )
    db_session.add(hold)
    db_session.flush()

    binding = LegalHoldBinding(
        binding_id="BIND-001",
        hold_id=hold.hold_id,
        artifact_id=artifact_id,
        case_id=None,
    )
    db_session.add(binding)
    db_session.commit()

    reloaded_hold = db_session.get(LegalHold, "HOLD-001")
    assert reloaded_hold is not None
    assert reloaded_hold.status == "ACTIVE"

    q = db_session.query(LegalHoldBinding).filter(LegalHoldBinding.artifact_id == artifact_id)
    bindings = q.all()
    assert len(bindings) == 1
    assert bindings[0].hold_id == "HOLD-001"


def test_deny_delete_under_legal_hold_includes_invariant_id(db_session: Session):
    artifact_id = "ART-01KKSMAP4MH6HWGM2RR9J22K79"

    # Seed evidence
    db_session.add(
        EvidenceArtifact(
            artifact_id=artifact_id,
            artifact_class="REQUIREMENT_EVIDENCE",
            producing_service="pytest",
            linked_case_id=None,
            linked_object_id=None,
            authoritativeness="authoritative",
            retention_class="CASE_CORE_7Y",
            checksum="sha256:" + ("0" * 64),
            storage_uri=f"s3://sps-evidence/evidence/01/{artifact_id}",
            content_bytes=None,
            content_type=None,
            provenance={"producer": "pytest"},
            created_at=_utcnow(),
            expires_at=None,
            legal_hold_flag=False,
        )
    )

    # Place hold + bind to artifact
    hold = LegalHold(
        hold_id="HOLD-001",
        reason="litigation hold",
        requested_by="Compliance Counsel",
        authorized_by="General Counsel",
        status="ACTIVE",
        released_at=None,
    )
    db_session.add(hold)
    db_session.flush()

    db_session.add(
        LegalHoldBinding(
            binding_id="BIND-001",
            hold_id=hold.hold_id,
            artifact_id=artifact_id,
            case_id=None,
        )
    )
    db_session.commit()

    client = TestClient(app)
    resp = client.delete(f"/api/v1/evidence/artifacts/{artifact_id}")

    assert resp.status_code == 423, resp.text
    detail = resp.json()["detail"]
    assert detail["invariant_id"] == "INV-004"
    assert detail["artifact_id"] == artifact_id


def test_dry_run_purge_excludes_held_artifacts(db_session: Session):
    now = _utcnow()

    eligible_id = "ART-01KKSMAP4MH6HWGM2RR9J22K80"
    held_id = "ART-01KKSMAP4MH6HWGM2RR9J22K81"

    db_session.add_all(
        [
            EvidenceArtifact(
                artifact_id=eligible_id,
                artifact_class="REQUIREMENT_EVIDENCE",
                producing_service="pytest",
                linked_case_id=None,
                linked_object_id=None,
                authoritativeness="authoritative",
                retention_class="CASE_CORE_7Y",
                checksum="sha256:" + ("0" * 64),
                storage_uri=f"s3://sps-evidence/evidence/01/{eligible_id}",
                content_bytes=None,
                content_type=None,
                provenance={"producer": "pytest"},
                created_at=now,
                expires_at=now - dt.timedelta(days=1),
                legal_hold_flag=False,
            ),
            EvidenceArtifact(
                artifact_id=held_id,
                artifact_class="REQUIREMENT_EVIDENCE",
                producing_service="pytest",
                linked_case_id=None,
                linked_object_id=None,
                authoritativeness="authoritative",
                retention_class="CASE_CORE_7Y",
                checksum="sha256:" + ("0" * 64),
                storage_uri=f"s3://sps-evidence/evidence/01/{held_id}",
                content_bytes=None,
                content_type=None,
                provenance={"producer": "pytest"},
                created_at=now,
                expires_at=now - dt.timedelta(days=1),
                legal_hold_flag=False,
            ),
        ]
    )

    hold = LegalHold(
        hold_id="HOLD-001",
        reason="litigation hold",
        requested_by="Compliance Counsel",
        authorized_by="General Counsel",
        status="ACTIVE",
        released_at=None,
    )
    db_session.add(hold)
    db_session.flush()

    db_session.add(
        LegalHoldBinding(
            binding_id="BIND-001",
            hold_id=hold.hold_id,
            artifact_id=held_id,
            case_id=None,
        )
    )

    db_session.commit()

    result = dry_run_purge(db=db_session, as_of=now)
    assert eligible_id in result.eligible_artifact_ids
    assert held_id not in result.eligible_artifact_ids
