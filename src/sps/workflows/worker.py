from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from sps.config import get_settings
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_jurisdiction_resolutions,
    persist_requirement_sets,
    persist_review_decision,
)
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import try_get_pydantic_data_converter

logger = logging.getLogger(__name__)


async def _run_worker() -> None:
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info(
        "temporal.worker.start temporal_address=%s namespace=%s task_queue=%s",
        settings.temporal_address,
        settings.temporal_namespace,
        settings.temporal_task_queue,
    )

    data_converter = try_get_pydantic_data_converter()

    try:
        client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            data_converter=data_converter,
        )
    except Exception as exc:
        logger.exception(
            "temporal.worker.connect_error temporal_address=%s namespace=%s exc_type=%s",
            settings.temporal_address,
            settings.temporal_namespace,
            type(exc).__name__,
        )
        raise

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            persist_jurisdiction_resolutions,
            persist_requirement_sets,
            apply_state_transition,
            persist_review_decision,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=10),
    )

    logger.info(
        "temporal.worker.polling namespace=%s task_queue=%s workflows=%s activities=%s",
        settings.temporal_namespace,
        settings.temporal_task_queue,
        [PermitCaseWorkflow.__name__],
        [
            ensure_permit_case_exists.__name__,
            fetch_permit_case_state.__name__,
            persist_jurisdiction_resolutions.__name__,
            persist_requirement_sets.__name__,
            apply_state_transition.__name__,
            persist_review_decision.__name__,
        ],
    )

    await worker.run()


def main() -> None:
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
