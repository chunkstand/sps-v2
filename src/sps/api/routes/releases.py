from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.api.routes.reviews import require_reviewer_api_key
from sps.config import get_settings
from sps.db.models import EvidenceArtifact as EvidenceArtifactRow
from sps.db.models import ReleaseArtifact, ReleaseBundle
from sps.db.session import get_db
from sps.documents.registry import EvidenceRegistry
from sps.evidence.models import ArtifactClass, EvidenceArtifact, RetentionClass
from sps.storage.s3 import IntegrityError as StorageIntegrityError
from sps.storage.s3 import S3Storage, StorageError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["releases"], dependencies=[Depends(require_reviewer_api_key)])


class ReleaseArtifactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    checksum: str = Field(min_length=1)
    storage_uri: str = Field(min_length=1)


class ReleaseBundleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_id: str = Field(min_length=1)
    spec_version: str = Field(min_length=1)
    app_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    policy_bundle_version: str = Field(min_length=1)
    invariant_pack_version: str = Field(min_length=1)
    adapter_versions: dict[str, str] = Field(default_factory=dict)
    artifact_digests: dict[str, str] = Field(default_factory=dict)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[ReleaseArtifactRequest] = Field(default_factory=list)


class ReleaseBundleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_id: str
    created_at: dt.datetime
    artifact_count: int = Field(ge=0)
    artifact_ids: list[str] = Field(default_factory=list)


class RollbackRehearsalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_id: str = Field(min_length=1)
    rehearsal_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    operator_id: str = Field(min_length=1)
    authoritativeness: str = Field(min_length=1)
    artifact_class: ArtifactClass = Field(default=ArtifactClass.ROLLBACK_REHEARSAL)
    checksum: str = Field(..., description="Expected checksum in format 'sha256:<hex>'")
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None

    @field_validator("checksum")
    @classmethod
    def _validate_checksum(cls, value: str) -> str:
        if not value.startswith("sha256:"):
            raise ValueError("checksum must be formatted as sha256:<hex>")
        hex_part = value.removeprefix("sha256:")
        if len(hex_part) != 64:
            raise ValueError("sha256 hex must be 64 chars")
        int(hex_part, 16)
        return value


def _validate_artifact_references(req: ReleaseBundleRequest) -> None:
    artifact_ids = [artifact.artifact_id for artifact in req.artifacts]
    duplicate_ids = sorted({item for item in artifact_ids if artifact_ids.count(item) > 1})
    if duplicate_ids:
        logger.warning(
            "release_bundle.invalid_artifacts error=duplicate_ids release_id=%s duplicate_ids=%s",
            req.release_id,
            duplicate_ids,
        )
        raise HTTPException(
            status_code=400,
            detail={"error": "duplicate_artifact_ids", "artifact_ids": duplicate_ids},
        )

    digest_ids = set(req.artifact_digests.keys())
    artifact_id_set = set(artifact_ids)

    missing_digests = sorted(artifact_id_set - digest_ids)
    unknown_digests = sorted(digest_ids - artifact_id_set)
    if missing_digests or unknown_digests:
        logger.warning(
            "release_bundle.invalid_artifacts error=digest_mismatch release_id=%s missing=%s unknown=%s",
            req.release_id,
            missing_digests,
            unknown_digests,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "artifact_digest_mismatch",
                "missing_digests": missing_digests,
                "unknown_digests": unknown_digests,
            },
        )


@router.post("/bundles", status_code=201, response_model=ReleaseBundleResponse)
def create_release_bundle(
    req: ReleaseBundleRequest,
    db: Session = Depends(get_db),
) -> ReleaseBundleResponse:
    """Persist a release bundle and its artifact rows."""
    _validate_artifact_references(req)

    created_at = dt.datetime.now(tz=dt.UTC)

    bundle_row = ReleaseBundle(
        release_id=req.release_id,
        spec_version=req.spec_version,
        app_version=req.app_version,
        schema_version=req.schema_version,
        model_version=req.model_version,
        policy_bundle_version=req.policy_bundle_version,
        invariant_pack_version=req.invariant_pack_version,
        adapter_versions=req.adapter_versions,
        artifact_digests=req.artifact_digests,
        approvals=req.approvals,
        created_at=created_at,
    )

    artifact_rows = [
        ReleaseArtifact(
            artifact_id=artifact.artifact_id,
            release_id=req.release_id,
            checksum=artifact.checksum,
            storage_uri=artifact.storage_uri,
            created_at=created_at,
        )
        for artifact in req.artifacts
    ]

    db.add(bundle_row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.warning(
            "release_bundle.conflict release_id=%s artifact_count=%d",
            req.release_id,
            len(artifact_rows),
        )
        raise HTTPException(
            status_code=409,
            detail={"error": "RELEASE_BUNDLE_ALREADY_EXISTS", "release_id": req.release_id},
        )

    db.add_all(artifact_rows)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning(
            "release_bundle.conflict release_id=%s artifact_count=%d",
            req.release_id,
            len(artifact_rows),
        )
        raise HTTPException(
            status_code=409,
            detail={"error": "RELEASE_BUNDLE_ALREADY_EXISTS", "release_id": req.release_id},
        )

    logger.info(
        "release_bundle.created release_id=%s artifact_count=%d",
        req.release_id,
        len(artifact_rows),
    )

    return ReleaseBundleResponse(
        release_id=req.release_id,
        created_at=created_at,
        artifact_count=len(artifact_rows),
        artifact_ids=[artifact.artifact_id for artifact in req.artifacts],
    )


@router.post("/rollbacks/rehearsals", status_code=201, response_model=EvidenceArtifact)
def create_rollback_rehearsal(
    req: RollbackRehearsalRequest,
    db: Session = Depends(get_db),
) -> EvidenceArtifact:
    """Persist rollback rehearsal evidence in the registry."""
    if req.artifact_class != ArtifactClass.ROLLBACK_REHEARSAL:
        logger.warning(
            "rollback_rehearsal.invalid_class release_id=%s rehearsal_id=%s class=%s",
            req.release_id,
            req.rehearsal_id,
            req.artifact_class.value,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_artifact_class",
                "artifact_class": req.artifact_class.value,
                "expected": ArtifactClass.ROLLBACK_REHEARSAL.value,
            },
        )

    payload_json = json.dumps(req.evidence_payload, sort_keys=True, separators=(",", ":"))
    payload_bytes = payload_json.encode("utf-8")
    actual_sha = hashlib.sha256(payload_bytes).hexdigest()
    expected_sha = req.checksum.removeprefix("sha256:")
    if actual_sha.lower() != expected_sha.lower():
        logger.warning(
            "rollback_rehearsal.checksum_mismatch release_id=%s rehearsal_id=%s",
            req.release_id,
            req.rehearsal_id,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "checksum_mismatch",
                "expected": req.checksum,
                "actual": f"sha256:{actual_sha}",
            },
        )

    settings = get_settings()
    storage = S3Storage(settings=settings)
    try:
        storage.ensure_bucket(settings.s3_bucket_evidence)
    except StorageError as exc:
        logger.warning(
            "rollback_rehearsal.storage_error release_id=%s rehearsal_id=%s error=%s",
            req.release_id,
            req.rehearsal_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail={"error": "s3_error", "msg": str(exc)})

    registry = EvidenceRegistry(storage=storage, settings=settings)
    try:
        registered = registry.register_manifest(
            content=payload_bytes,
            case_id=req.release_id,
            provenance={"release_id": req.release_id, "rehearsal_id": req.rehearsal_id},
        )
    except StorageIntegrityError as exc:
        logger.warning(
            "rollback_rehearsal.storage_integrity_error release_id=%s rehearsal_id=%s error=%s",
            req.release_id,
            req.rehearsal_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=422, detail={"error": "integrity_error", "msg": str(exc)})
    except StorageError as exc:
        logger.warning(
            "rollback_rehearsal.storage_error release_id=%s rehearsal_id=%s error=%s",
            req.release_id,
            req.rehearsal_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail={"error": "s3_error", "msg": str(exc)})

    created_at = dt.datetime.now(tz=dt.UTC)
    provenance = {
        "release_id": req.release_id,
        "rehearsal_id": req.rehearsal_id,
        "environment": req.environment,
        "operator_id": req.operator_id,
        "notes": req.notes,
    }
    provenance = {key: value for key, value in provenance.items() if value is not None}

    row = EvidenceArtifactRow(
        artifact_id=registered.artifact_id,
        artifact_class=ArtifactClass.ROLLBACK_REHEARSAL.value,
        producing_service="release_api",
        linked_case_id=None,
        linked_object_id=req.release_id,
        authoritativeness=req.authoritativeness,
        retention_class=RetentionClass.RELEASE_EVIDENCE.value,
        checksum=req.checksum,
        storage_uri=registered.storage_uri,
        content_bytes=registered.content_bytes,
        content_type="application/json",
        provenance=provenance,
        created_at=created_at,
        expires_at=None,
        legal_hold_flag=False,
    )

    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "rollback_rehearsal.persistence_failed release_id=%s rehearsal_id=%s error=%s",
            req.release_id,
            req.rehearsal_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=409,
            detail={"error": "ROLLBACK_REHEARSAL_ALREADY_EXISTS", "release_id": req.release_id},
        )

    logger.info(
        "rollback_rehearsal.created release_id=%s rehearsal_id=%s artifact_id=%s",
        req.release_id,
        req.rehearsal_id,
        row.artifact_id,
    )

    return EvidenceArtifact(
        artifact_id=row.artifact_id,
        artifact_class=ArtifactClass.ROLLBACK_REHEARSAL,
        producing_service=row.producing_service or "",
        linked_case_id=row.linked_case_id,
        linked_object_id=row.linked_object_id,
        retention_class=RetentionClass.RELEASE_EVIDENCE,
        checksum=row.checksum,
        storage_uri=row.storage_uri,
        authoritativeness=row.authoritativeness,
        provenance=row.provenance or {},
        created_at=row.created_at,
        expires_at=row.expires_at,
        legal_hold_flag=row.legal_hold_flag,
    )
