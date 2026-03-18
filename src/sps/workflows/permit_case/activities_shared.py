from __future__ import annotations

import logging

from temporalio import activity

logger = logging.getLogger("sps.workflows.permit_case.activities_impl")


def safe_temporal_ids() -> tuple[str | None, str | None]:
    """Best-effort activity correlation identifiers."""

    try:
        info = activity.info()
        return info.workflow_id, info.workflow_run_id
    except Exception:
        return None, None
