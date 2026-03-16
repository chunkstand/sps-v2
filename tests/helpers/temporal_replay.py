from __future__ import annotations

from typing import Any, Sequence

from temporalio.client import WorkflowHistory
from temporalio.worker import Replayer, WorkflowReplayResult

from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import try_get_pydantic_data_converter


async def replay_permit_case_workflow_history(
    history: WorkflowHistory | str | dict[str, Any],
    *,
    workflow_id: str | None = None,
    raise_on_replay_failure: bool = True,
) -> WorkflowReplayResult:
    """Replay a PermitCaseWorkflow history offline.

    Args:
        history:
            A WorkflowHistory fetched from a real workflow run via
            ``await WorkflowHandle.fetch_history()``.

            For convenience, this can also be a JSON string/dict in the format
            produced by Temporal UI/CLI exports; in that case ``workflow_id`` is
            required.
        workflow_id: Required when ``history`` is JSON.
        raise_on_replay_failure:
            Passed through to ``Replayer.replay_workflow``. When True, any
            non-determinism raises.

    Returns:
        WorkflowReplayResult. If ``raise_on_replay_failure`` is True, returning
        implies determinism for this history.
    """

    if isinstance(history, WorkflowHistory):
        parsed = history
    else:
        if workflow_id is None:
            raise ValueError("workflow_id is required when replaying from JSON history")
        parsed = WorkflowHistory.from_json(workflow_id, history)

    # Important: use the same converter wiring as the live client. Otherwise we
    # can fail to hydrate Pydantic workflow inputs/signals during replay.
    replayer = Replayer(
        workflows=[PermitCaseWorkflow],
        data_converter=try_get_pydantic_data_converter(),
    )
    return await replayer.replay_workflow(
        parsed, raise_on_replay_failure=raise_on_replay_failure
    )


async def replay_workflow_history(
    history: WorkflowHistory,
    *,
    workflows: Sequence[type],
    raise_on_replay_failure: bool = True,
) -> WorkflowReplayResult:
    """Generic offline replay helper for other workflows.

    Prefer the workflow-specific helper when you want deterministic wiring
    (converter, workflow list).
    """

    replayer = Replayer(
        workflows=list(workflows),
        data_converter=try_get_pydantic_data_converter(),
    )
    return await replayer.replay_workflow(
        history, raise_on_replay_failure=raise_on_replay_failure
    )
