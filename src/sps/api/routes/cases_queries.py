from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sps.db.models import EvidenceArtifact, PermitCase, SubmissionPackage

from .cases_support import logger


def get_case_or_404(
    db: Session,
    case_id: str,
    *,
    missing_case_event: str,
) -> PermitCase:
    case = db.get(PermitCase, case_id)
    if case is None:
        logger.warning("%s case_id=%s", missing_case_event, case_id)
        raise HTTPException(
            status_code=404,
            detail={"error": "case_not_found", "case_id": case_id},
        )
    return case


def fetch_case_rows(
    db: Session,
    *,
    case_id: str,
    model: Any,
    limit: int,
    order_by: Sequence[Any],
    missing_case_event: str,
    failure_event: str,
    failure_error: str,
    missing_rows_event: str | None = None,
    not_ready_error: str | None = None,
    missing_name: str | None = None,
) -> list[Any]:
    get_case_or_404(db, case_id, missing_case_event=missing_case_event)
    try:
        rows = (
            db.query(model)
            .filter(model.case_id == case_id)
            .order_by(*order_by)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception("%s case_id=%s exc_type=%s", failure_event, case_id, type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail={"error": failure_error, "case_id": case_id},
        ) from exc

    if not rows and not_ready_error and missing_rows_event and missing_name:
        logger.warning("%s case_id=%s", missing_rows_event, case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": not_ready_error,
                "case_id": case_id,
                "missing": missing_name,
            },
        )

    return rows


def fetch_artifact_map(
    db: Session,
    artifact_ids: Iterable[str],
    *,
    missing_event: str,
    case_id: str,
) -> dict[str, EvidenceArtifact]:
    artifact_ids = [artifact_id for artifact_id in artifact_ids if artifact_id]
    if not artifact_ids:
        return {}

    rows = (
        db.query(EvidenceArtifact)
        .filter(EvidenceArtifact.artifact_id.in_(artifact_ids))
        .all()
    )
    artifact_map = {row.artifact_id: row for row in rows}
    missing_ids = set(artifact_ids) - set(artifact_map)
    for missing_id in missing_ids:
        logger.warning("%s case_id=%s artifact_id=%s", missing_event, case_id, missing_id)
    return artifact_map


def get_current_submission_package(db: Session, case_id: str) -> SubmissionPackage:
    try:
        case = get_case_or_404(db, case_id, missing_case_event="cases.package_missing_case")
        if case.current_package_id is None:
            logger.warning("cases.package_not_ready case_id=%s", case_id)
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "package_not_ready",
                    "case_id": case_id,
                    "missing": "current_package_id",
                },
            )

        package = db.get(SubmissionPackage, case.current_package_id)
        if package is None:
            logger.error(
                "cases.package_missing case_id=%s package_id=%s",
                case_id,
                case.current_package_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "package_reference_broken",
                    "case_id": case_id,
                    "package_id": case.current_package_id,
                },
            )
        return package
    except SQLAlchemyError as exc:
        logger.exception("cases.package_fetch_failed case_id=%s exc_type=%s", case_id, type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail={"error": "package_fetch_failed", "case_id": case_id},
        ) from exc


def get_manifest_artifact_for_case(db: Session, case_id: str) -> tuple[SubmissionPackage, EvidenceArtifact]:
    try:
        case = get_case_or_404(db, case_id, missing_case_event="cases.manifest_missing_case")
        if case.current_package_id is None:
            logger.warning("cases.manifest_not_ready case_id=%s", case_id)
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "manifest_not_ready",
                    "case_id": case_id,
                    "missing": "current_package_id",
                },
            )

        package = db.get(SubmissionPackage, case.current_package_id)
        if package is None:
            logger.error(
                "cases.manifest_package_missing case_id=%s package_id=%s",
                case_id,
                case.current_package_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "package_reference_broken",
                    "case_id": case_id,
                    "package_id": case.current_package_id,
                },
            )

        manifest_artifact = db.get(EvidenceArtifact, package.manifest_artifact_id)
        if manifest_artifact is None:
            logger.error(
                "cases.manifest_artifact_missing case_id=%s artifact_id=%s",
                case_id,
                package.manifest_artifact_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "manifest_artifact_missing",
                    "case_id": case_id,
                    "artifact_id": package.manifest_artifact_id,
                },
            )
        return package, manifest_artifact
    except SQLAlchemyError as exc:
        logger.exception("cases.manifest_fetch_failed case_id=%s exc_type=%s", case_id, type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail={"error": "manifest_fetch_failed", "case_id": case_id},
        ) from exc
