from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.config import get_settings
from sps.db.models import EvidenceArtifact as EvidenceArtifactRow
from sps.db.session import get_db
from sps.evidence.ids import evidence_object_key, new_evidence_id
from sps.evidence.models import ArtifactClass, EvidenceArtifact, RetentionClass
from sps.retention.guard import InvariantDenied, assert_not_on_legal_hold
from sps.storage.s3 import IntegrityError as StorageIntegrityError
from sps.storage.s3 import S3Storage, StorageError

router = APIRouter(tags=["evidence"])


def _get_storage() -> S3Storage:
    return S3Storage(get_settings())


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


class EvidenceRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_class: ArtifactClass
    producing_service: str

    linked_case_id: str | None = None
    linked_object_id: str | None = None

    retention_class: RetentionClass
    checksum: str = Field(..., description="Expected checksum in format 'sha256:<hex>'")
    authoritativeness: str
    provenance: dict[str, Any]

    expires_at: dt.datetime | None = None

    @field_validator("checksum")
    @classmethod
    def _validate_checksum(cls, value: str) -> str:
        if not value.startswith("sha256:"):
            raise ValueError("checksum must be formatted as sha256:<hex>")
        hex_part = value.removeprefix("sha256:")
        if len(hex_part) != 64:
            raise ValueError("sha256 hex must be 64 chars")
        int(hex_part, 16)  # raises if non-hex
        return value


@router.post("/evidence/artifacts", status_code=201)
def register_evidence_artifact(req: EvidenceRegisterRequest, db: Session = Depends(get_db)):
    artifact_id = new_evidence_id()

    settings = get_settings()
    bucket = settings.s3_bucket_evidence
    key = evidence_object_key(artifact_id)
    storage_uri = f"s3://{bucket}/{key}"

    row = EvidenceArtifactRow(
        artifact_id=artifact_id,
        artifact_class=req.artifact_class.value,
        producing_service=req.producing_service,
        linked_case_id=req.linked_case_id,
        linked_object_id=req.linked_object_id,
        retention_class=req.retention_class.value,
        checksum=req.checksum,
        storage_uri=storage_uri,
        authoritativeness=req.authoritativeness,
        provenance=req.provenance,
        created_at=_utcnow(),
        expires_at=req.expires_at,
        legal_hold_flag=False,
        content_bytes=None,
        content_type=None,
    )

    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={"error": "conflict", "msg": str(e)})

    return EvidenceArtifact(
        artifact_id=row.artifact_id,
        artifact_class=req.artifact_class,
        producing_service=row.producing_service or "",
        linked_case_id=row.linked_case_id,
        linked_object_id=row.linked_object_id,
        retention_class=req.retention_class,
        checksum=row.checksum,
        storage_uri=row.storage_uri,
        authoritativeness=row.authoritativeness,
        provenance=row.provenance or {},
        created_at=row.created_at,
        expires_at=row.expires_at,
        legal_hold_flag=row.legal_hold_flag,
    )


@router.put("/evidence/artifacts/{artifact_id}/content")
def upload_evidence_content(
    artifact_id: str,
    content: bytes = Body(...),
    content_type: str | None = Header(default=None, alias="content-type"),
    db: Session = Depends(get_db),
):
    row = db.get(EvidenceArtifactRow, artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"artifact_id": artifact_id, "error": "not_found"})

    if not row.checksum.startswith("sha256:"):
        raise HTTPException(status_code=422, detail={"artifact_id": artifact_id, "error": "invalid_checksum_format"})

    expected_sha = row.checksum.removeprefix("sha256:")
    actual_sha = hashlib.sha256(content).hexdigest()
    if expected_sha.lower() != actual_sha.lower():
        raise HTTPException(
            status_code=422,
            detail={
                "artifact_id": artifact_id,
                "error": "sha_mismatch",
                "expected": row.checksum,
                "actual": f"sha256:{actual_sha}",
            },
        )

    settings = get_settings()
    storage = _get_storage()

    bucket = settings.s3_bucket_evidence
    key = evidence_object_key(artifact_id)

    try:
        storage.ensure_bucket(bucket)
        storage.put_bytes(
            bucket=bucket,
            key=key,
            content=content,
            expected_sha256_hex=expected_sha,
            expected_bytes=len(content),
            content_type=content_type,
        )
    except StorageIntegrityError as e:
        raise HTTPException(status_code=422, detail={"artifact_id": artifact_id, "error": "integrity_error", "msg": str(e)})
    except StorageError as e:
        raise HTTPException(status_code=502, detail={"artifact_id": artifact_id, "error": "s3_error", "msg": str(e)})

    row.content_bytes = len(content)
    row.content_type = content_type

    try:
        db.commit()
    except Exception as e:  # pragma: no cover
        db.rollback()
        raise HTTPException(status_code=500, detail={"artifact_id": artifact_id, "error": "db_commit_failed", "msg": str(e)})

    return {"artifact_id": artifact_id, "bytes": row.content_bytes, "checksum": row.checksum}


@router.get("/evidence/artifacts/{artifact_id}")
def get_evidence_metadata(artifact_id: str, db: Session = Depends(get_db)):
    row = db.get(EvidenceArtifactRow, artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"artifact_id": artifact_id, "error": "not_found"})

    return {
        "artifact_id": row.artifact_id,
        "artifact_class": row.artifact_class,
        "producing_service": row.producing_service,
        "linked_case_id": row.linked_case_id,
        "linked_object_id": row.linked_object_id,
        "retention_class": row.retention_class,
        "checksum": row.checksum,
        "storage_uri": row.storage_uri,
        "authoritativeness": row.authoritativeness,
        "provenance": row.provenance,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "legal_hold_flag": row.legal_hold_flag,
        "content_bytes": row.content_bytes,
        "content_type": row.content_type,
    }


@router.get("/evidence/artifacts/{artifact_id}/download")
def get_evidence_download_link(artifact_id: str, db: Session = Depends(get_db)):
    row = db.get(EvidenceArtifactRow, artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"artifact_id": artifact_id, "error": "not_found"})

    settings = get_settings()
    storage = _get_storage()
    bucket = settings.s3_bucket_evidence
    key = evidence_object_key(artifact_id)

    try:
        url = storage.presign_get(bucket=bucket, key=key)
    except StorageError:
        raise HTTPException(status_code=502, detail={"artifact_id": artifact_id, "error": "s3_error"})

    return {"artifact_id": artifact_id, "url": url}


@router.delete("/evidence/artifacts/{artifact_id}")
def delete_evidence_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Destructive delete entrypoint (guarded by INV-004).

    Phase 1 keeps actual deletion disabled; this exists to prove legal-hold denial behavior.
    """

    row = db.get(EvidenceArtifactRow, artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"artifact_id": artifact_id, "error": "not_found"})

    try:
        assert_not_on_legal_hold(db=db, artifact_id=artifact_id, operation="delete_evidence_artifact")
    except InvariantDenied as e:
        raise HTTPException(status_code=423, detail=e.to_dict())

    raise HTTPException(status_code=501, detail={"artifact_id": artifact_id, "error": "delete_not_enabled_in_phase1"})
