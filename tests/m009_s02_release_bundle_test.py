"""M009 / S02 integration tests: release blockers + bundle persistence.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.

Checks:
  - /api/v1/ops/release-blockers returns scoped blockers.
  - POST /api/v1/releases/bundles persists bundle + artifact rows.
  - Artifact digest mismatches return structured 400 errors.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import (
    ContradictionArtifact,
    DissentArtifact,
    PermitCase,
    ReleaseArtifact,
    ReleaseBundle,
    ReviewDecision,
)
from sps.db.session import get_engine, get_sessionmaker
from sps.services.release_bundle_manifest import (
    ReleaseBundleManifestError,
    build_release_bundle_components,
)


if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal/Postgres integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
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
            time.sleep(0.5)

    raise RuntimeError(
        f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE release_artifacts, release_bundles, dissent_artifacts, "
                "review_decisions, contradiction_artifacts, permit_cases CASCADE"
            )
        )


def _seed_permit_case(case_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-test",
                project_id=f"project-{case_id}",
                case_state="REVIEW_PENDING",
                review_state="PENDING",
                submission_mode="DIGITAL",
                portal_support_level="FULL",
                current_package_id=None,
                current_release_profile="default",
                legal_hold=False,
                closure_reason=None,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )
        session.commit()


def _seed_review_decision(case_id: str, decision_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            ReviewDecision(
                decision_id=decision_id,
                schema_version="2026-01-01",
                case_id=case_id,
                object_type="PERMIT_CASE",
                object_id=case_id,
                decision_outcome="ACCEPT_WITH_DISSENT",
                reviewer_id="reviewer-test",
                subject_author_id="author-test",
                reviewer_independence_status="INDEPENDENT",
                evidence_ids=[],
                contradiction_resolution=None,
                dissent_flag=True,
                notes=None,
                decision_at=_utcnow(),
                idempotency_key=f"idem/{decision_id}",
                created_at=_utcnow(),
            )
        )
        session.commit()


def _seed_dissent(
    *,
    dissent_id: str,
    case_id: str,
    linked_review_id: str,
    scope: str,
    resolution_state: str = "OPEN",
) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            DissentArtifact(
                dissent_id=dissent_id,
                linked_review_id=linked_review_id,
                case_id=case_id,
                scope=scope,
                rationale="rationale",
                required_followup=None,
                resolution_state=resolution_state,
                created_at=_utcnow(),
            )
        )
        session.commit()


def _seed_contradiction(
    *,
    contradiction_id: str,
    case_id: str,
    blocking_effect: bool,
    resolution_status: str,
) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            ContradictionArtifact(
                contradiction_id=contradiction_id,
                case_id=case_id,
                scope="RELEASE",
                source_a="source-a",
                source_b="source-b",
                ranking_relation="SAME_RANK",
                blocking_effect=blocking_effect,
                resolution_status=resolution_status,
                resolved_at=_utcnow() if resolution_status != "OPEN" else None,
                resolved_by="reviewer-test" if resolution_status != "OPEN" else None,
                created_at=_utcnow(),
            )
        )
        session.commit()


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_temp_manifest(
    tmp_path: Path,
    *,
    bad_hash: bool = False,
    root_dir: Path | None = None,
) -> tuple[Path, Path]:
    root_dir = root_dir or tmp_path
    artifact_path = root_dir / "artifact.yaml"
    artifact_path.write_text(
        """---\nartifact_metadata:\n  artifact_id: ART-TEST-001\n---\nname: test\n""",
        encoding="utf-8",
    )
    content = artifact_path.read_bytes()
    sha = _hash_bytes(content)
    if bad_hash:
        sha = "0" * len(sha)
    manifest_payload = [
        {"path": artifact_path.name, "sha256": sha, "bytes": len(content)},
    ]
    manifest_path = root_dir / "PACKAGE-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
    return manifest_path, root_dir


def _run_release_bundle_cli(
    args: list[str],
    env: dict[str, str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(repo_root / "scripts/generate_release_bundle.py"), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd or repo_root,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _db_lifecycle() -> Generator[None, None, None]:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()
    yield
    _reset_db()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_release_blockers_endpoint_filters_scope() -> None:
    settings = get_settings()

    case_id = "CASE-REL-BLOCK-001"
    decision_id = "DEC-REL-BLOCK-001"
    decision_id_low = "DEC-REL-BLOCK-LOW"

    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)
    _seed_review_decision(case_id, decision_id_low)

    _seed_dissent(
        dissent_id="DISSENT-HIGH-RISK",
        case_id=case_id,
        linked_review_id=decision_id,
        scope="PERMIT/HIGH_RISK",
    )
    _seed_dissent(
        dissent_id="DISSENT-LOW-RISK",
        case_id=case_id,
        linked_review_id=decision_id_low,
        scope="PERMIT/LOW_RISK",
    )

    _seed_contradiction(
        contradiction_id="CONTRA-OPEN-BLOCKING",
        case_id=case_id,
        blocking_effect=True,
        resolution_status="OPEN",
    )
    _seed_contradiction(
        contradiction_id="CONTRA-OPEN-NONBLOCK",
        case_id=case_id,
        blocking_effect=False,
        resolution_status="OPEN",
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/ops/release-blockers",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
        )

    assert response.status_code == 200, (
        "Expected 200 from /api/v1/ops/release-blockers, "
        f"got {response.status_code}: {response.text}"
    )

    payload = response.json()
    assert payload["blocker_count"] == 2

    contradiction_ids = {item["contradiction_id"] for item in payload["contradictions"]}
    dissent_ids = {item["dissent_id"] for item in payload["dissents"]}

    assert "CONTRA-OPEN-BLOCKING" in contradiction_ids
    assert "DISSENT-HIGH-RISK" in dissent_ids
    assert "DISSENT-LOW-RISK" not in dissent_ids


@pytest.mark.anyio
async def test_release_bundle_persists_rows() -> None:
    settings = get_settings()

    release_id = "REL-2026-03-16"

    request_body = {
        "release_id": release_id,
        "spec_version": "spec-1",
        "app_version": "app-1",
        "schema_version": "schema-1",
        "model_version": "model-1",
        "policy_bundle_version": "policy-1",
        "invariant_pack_version": "inv-1",
        "adapter_versions": {"adapter-a": "1.0"},
        "artifact_digests": {"ART-1": "digest-1", "ART-2": "digest-2"},
        "approvals": [{"reviewer": "ops", "status": "APPROVED"}],
        "artifacts": [
            {"artifact_id": "ART-1", "checksum": "sha256-1", "storage_uri": "s3://bucket/a"},
            {"artifact_id": "ART-2", "checksum": "sha256-2", "storage_uri": "s3://bucket/b"},
        ],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/releases/bundles",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json=request_body,
        )

    assert response.status_code == 201, (
        "Expected 201 from POST /api/v1/releases/bundles, "
        f"got {response.status_code}: {response.text}"
    )

    payload = response.json()
    assert payload["release_id"] == release_id
    assert payload["artifact_count"] == 2

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        bundle_row = session.get(ReleaseBundle, release_id)
        assert bundle_row is not None, "ReleaseBundle row not found"

        artifacts = (
            session.query(ReleaseArtifact)
            .filter(ReleaseArtifact.release_id == release_id)
            .order_by(ReleaseArtifact.artifact_id.asc())
            .all()
        )

    assert bundle_row.created_at is not None
    assert len(artifacts) == 2
    assert all(artifact.created_at == bundle_row.created_at for artifact in artifacts)


@pytest.mark.anyio
async def test_release_bundle_rejects_mismatched_artifact_digests() -> None:
    settings = get_settings()

    request_body = {
        "release_id": "REL-2026-03-16-BAD",
        "spec_version": "spec-1",
        "app_version": "app-1",
        "schema_version": "schema-1",
        "model_version": "model-1",
        "policy_bundle_version": "policy-1",
        "invariant_pack_version": "inv-1",
        "adapter_versions": {},
        "artifact_digests": {"ART-1": "digest-1"},
        "approvals": [],
        "artifacts": [
            {"artifact_id": "ART-1", "checksum": "sha256-1", "storage_uri": "s3://bucket/a"},
            {"artifact_id": "ART-2", "checksum": "sha256-2", "storage_uri": "s3://bucket/b"},
        ],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/releases/bundles",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json=request_body,
        )

    assert response.status_code == 400, (
        "Expected 400 from POST /api/v1/releases/bundles, "
        f"got {response.status_code}: {response.text}"
    )

    payload = response.json()
    assert payload["detail"]["error"] == "artifact_digest_mismatch"
    assert "ART-2" in payload["detail"]["missing_digests"]


def test_release_bundle_cli_success(tmp_path: Path) -> None:
    settings = get_settings()
    manifest_path, root_dir = _write_temp_manifest(tmp_path)

    env = os.environ.copy()
    env["API_BASE"] = "http://test"
    env["SPS_REVIEWER_API_KEY"] = settings.reviewer_api_key
    env["SPS_RELEASE_BUNDLE_HTTP_MODE"] = "asgi"

    result = _run_release_bundle_cli(
        [
            "--manifest",
            str(manifest_path),
            "--root",
            str(root_dir),
            "--release-id",
            "REL-CLI-OK",
        ],
        env,
    )

    assert result.returncode == 0, result.stderr

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        bundle_row = session.get(ReleaseBundle, "REL-CLI-OK")
        assert bundle_row is not None
        assert bundle_row.adapter_versions["city_portal_family_a"] == "2026-03-17.1"
        assert bundle_row.adapter_versions["phaniville_manual"] == "2026-03-17.1"


def test_release_bundle_manifest_missing_file_raises(tmp_path: Path) -> None:
    settings = get_settings()
    manifest_path = tmp_path / "PACKAGE-MANIFEST.json"
    manifest_path.write_text(
        json.dumps([{"path": "missing.yaml", "sha256": "0" * 64, "bytes": 1}]),
        encoding="utf-8",
    )

    with pytest.raises(ReleaseBundleManifestError, match="path does not exist"):
        build_release_bundle_components(
            manifest_path=manifest_path,
            root_dir=tmp_path,
            release_id="REL-MISSING-FILE",
            settings=settings,
            schema_path=Path(__file__).resolve().parents[1]
            / "model/sps/contracts/release-bundle-manifest.schema.json",
        )


def test_release_bundle_manifest_missing_artifact_id_raises(tmp_path: Path) -> None:
    settings = get_settings()
    artifact_path = tmp_path / "artifact.yaml"
    artifact_path.write_text("name: no artifact id\n", encoding="utf-8")
    manifest_path = tmp_path / "PACKAGE-MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "path": artifact_path.name,
                    "sha256": _hash_bytes(artifact_path.read_bytes()),
                    "bytes": len(artifact_path.read_bytes()),
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReleaseBundleManifestError, match="missing artifact_id"):
        build_release_bundle_components(
            manifest_path=manifest_path,
            root_dir=tmp_path,
            release_id="REL-MISSING-ARTIFACT-ID",
            settings=settings,
            schema_path=Path(__file__).resolve().parents[1]
            / "model/sps/contracts/release-bundle-manifest.schema.json",
        )


def test_release_bundle_cli_dry_run_surfaces_runtime_adapter_versions(tmp_path: Path) -> None:
    settings = get_settings()
    manifest_path, root_dir = _write_temp_manifest(tmp_path)

    env = os.environ.copy()
    env["API_BASE"] = "http://test"
    env["SPS_REVIEWER_API_KEY"] = settings.reviewer_api_key
    env["SPS_RELEASE_BUNDLE_HTTP_MODE"] = "asgi"

    result = _run_release_bundle_cli(
        [
            "--manifest",
            str(manifest_path),
            "--root",
            str(root_dir),
            "--release-id",
            "REL-CLI-DRY-RUN",
            "--dry-run",
        ],
        env,
    )

    assert result.returncode == 0, result.stderr
    assert '"city_portal_family_a": "2026-03-17.1"' in result.stdout
    assert '"phaniville_manual": "2026-03-17.1"' in result.stdout


def test_release_bundle_cli_manifest_path_includes_root(tmp_path: Path) -> None:
    settings = get_settings()
    root_dir = tmp_path / "sps_full_spec_package"
    root_dir.mkdir()
    _write_temp_manifest(tmp_path, root_dir=root_dir)

    env = os.environ.copy()
    env["API_BASE"] = "http://test"
    env["SPS_REVIEWER_API_KEY"] = settings.reviewer_api_key
    env["SPS_RELEASE_BUNDLE_HTTP_MODE"] = "asgi"

    result = _run_release_bundle_cli(
        [
            "--manifest",
            "sps_full_spec_package/PACKAGE-MANIFEST.json",
            "--root",
            "sps_full_spec_package",
            "--release-id",
            "REL-CLI-ROOTPATH",
        ],
        env,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        bundle_row = session.get(ReleaseBundle, "REL-CLI-ROOTPATH")
        assert bundle_row is not None


def test_release_bundle_cli_manifest_mismatch(tmp_path: Path) -> None:
    settings = get_settings()
    manifest_path, root_dir = _write_temp_manifest(tmp_path, bad_hash=True)

    env = os.environ.copy()
    env["API_BASE"] = "http://test"
    env["SPS_REVIEWER_API_KEY"] = settings.reviewer_api_key
    env["SPS_RELEASE_BUNDLE_HTTP_MODE"] = "asgi"

    result = _run_release_bundle_cli(
        [
            "--manifest",
            str(manifest_path),
            "--root",
            str(root_dir),
            "--release-id",
            "REL-CLI-BAD",
        ],
        env,
    )

    assert result.returncode != 0
    assert "release_bundle.manifest_invalid" in result.stderr


def test_release_bundle_cli_blockers(tmp_path: Path) -> None:
    settings = get_settings()
    manifest_path, root_dir = _write_temp_manifest(tmp_path)

    case_id = "CASE-CLI-BLOCK"
    decision_id = "DEC-CLI-BLOCK"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)
    _seed_dissent(
        dissent_id="DISSENT-CLI-001",
        case_id=case_id,
        linked_review_id=decision_id,
        scope="PERMIT/HIGH_RISK",
    )
    _seed_contradiction(
        contradiction_id="CONTRA-CLI-001",
        case_id=case_id,
        blocking_effect=True,
        resolution_status="OPEN",
    )

    env = os.environ.copy()
    env["API_BASE"] = "http://test"
    env["SPS_REVIEWER_API_KEY"] = settings.reviewer_api_key
    env["SPS_RELEASE_BUNDLE_HTTP_MODE"] = "asgi"

    result = _run_release_bundle_cli(
        [
            "--manifest",
            str(manifest_path),
            "--root",
            str(root_dir),
            "--release-id",
            "REL-CLI-BLOCK",
        ],
        env,
    )

    assert result.returncode != 0
    assert "release_bundle.blocked" in result.stderr
