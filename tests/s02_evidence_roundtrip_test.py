from __future__ import annotations

import hashlib

import pytest
import requests
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from sps.api.main import app
from sps.db.session import get_engine


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def _clean_evidence_table() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("TRUNCATE TABLE evidence_artifacts CASCADE"))


def test_evidence_roundtrip_register_upload_fetch_download(_clean_evidence_table):
    client = TestClient(app)

    content = b"hello-evidence"
    sha = hashlib.sha256(content).hexdigest()

    register_resp = client.post(
        "/api/v1/evidence/artifacts",
        json={
            "artifact_class": "REQUIREMENT_EVIDENCE",
            "producing_service": "pytest",
            "linked_case_id": None,
            "linked_object_id": None,
            "retention_class": "CASE_CORE_7Y",
            "checksum": f"sha256:{sha}",
            "authoritativeness": "authoritative",
            "provenance": {"producer": "pytest"},
        },
    )
    assert register_resp.status_code == 201, register_resp.text
    registered = register_resp.json()
    artifact_id = registered["artifact_id"]

    upload_resp = client.put(
        f"/api/v1/evidence/artifacts/{artifact_id}/content",
        content=content,
        headers={"content-type": "application/octet-stream"},
    )
    assert upload_resp.status_code == 200, upload_resp.text

    meta_resp = client.get(f"/api/v1/evidence/artifacts/{artifact_id}")
    assert meta_resp.status_code == 200, meta_resp.text
    meta = meta_resp.json()
    assert meta["artifact_id"] == artifact_id
    assert meta["checksum"] == f"sha256:{sha}"
    assert meta["content_bytes"] == len(content)

    dl_resp = client.get(f"/api/v1/evidence/artifacts/{artifact_id}/download")
    assert dl_resp.status_code == 200, dl_resp.text
    url = dl_resp.json()["url"]

    r = requests.get(url, timeout=10)
    assert r.status_code == 200
    assert r.content == content


def test_evidence_upload_rejects_sha_mismatch(_clean_evidence_table):
    client = TestClient(app)

    good = b"good"
    bad = b"bad"
    sha = hashlib.sha256(good).hexdigest()

    register_resp = client.post(
        "/api/v1/evidence/artifacts",
        json={
            "artifact_class": "REQUIREMENT_EVIDENCE",
            "producing_service": "pytest",
            "retention_class": "CASE_CORE_7Y",
            "checksum": f"sha256:{sha}",
            "authoritativeness": "authoritative",
            "provenance": {"producer": "pytest"},
        },
    )
    assert register_resp.status_code == 201
    artifact_id = register_resp.json()["artifact_id"]

    upload_resp = client.put(
        f"/api/v1/evidence/artifacts/{artifact_id}/content",
        content=bad,
        headers={"content-type": "application/octet-stream"},
    )
    assert upload_resp.status_code == 422
