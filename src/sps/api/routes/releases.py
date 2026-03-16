from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.api.routes.reviews import require_reviewer_api_key
from sps.db.models import ReleaseArtifact, ReleaseBundle
from sps.db.session import get_db

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
