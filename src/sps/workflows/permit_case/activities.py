from __future__ import annotations

import logging

from temporalio import activity

from sps.db.models import PermitCase
from sps.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


@activity.defn
def ensure_permit_case_exists(case_id: str) -> bool:
    """Ensure a minimal `permit_cases` row exists.

    This proves the determinism boundary: all DB I/O happens in an activity, not
    in workflow code.

    Returns:
        True if the row was created, False if it already existed.
    """

    info = activity.info()
    logger.info(
        "activity.start name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s",
        info.workflow_id,
        info.workflow_run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    created = False

    try:
        with SessionLocal() as session:
            existing = session.get(PermitCase, case_id)
            if existing is None:
                created = True
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-local",
                        project_id=f"project-{case_id}",
                        case_state="NEW",
                        review_state="PENDING",
                        submission_mode="PORTAL",
                        portal_support_level="SELF_SERVICE",
                        current_package_id=None,
                        current_release_profile="default",
                        closure_reason=None,
                    )
                )
                session.commit()

        logger.info(
            "activity.ok name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s created=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            created,
        )
        return created
    except Exception as exc:
        # Temporal will record the exception; this log line provides a grep-able correlation tuple.
        logger.exception(
            "activity.error name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            type(exc).__name__,
        )
        raise
