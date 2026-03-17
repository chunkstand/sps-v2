from __future__ import annotations

import argparse
import asyncio
import json
import logging
from temporalio.client import WorkflowHandle

from sps.config import get_settings
from sps.workflows.permit_case.contracts import (
    PermitCaseWorkflowInput,
    ReviewDecisionOutcome,
    ReviewDecisionSignal,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client
from sps.logging.redaction import attach_redaction_filter

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sps.workflows.cli",
        description="Operator CLI for PermitCaseWorkflow (Temporal)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a PermitCaseWorkflow")
    start.add_argument("--case-id", required=True)

    signal = sub.add_parser(
        "signal-review",
        help="Send ReviewDecision signal to a running PermitCaseWorkflow",
    )
    signal.add_argument("--case-id", required=True)
    signal.add_argument(
        "--decision-outcome",
        required=True,
        choices=[e.value for e in ReviewDecisionOutcome],
        help="ACCEPT, ACCEPT_WITH_DISSENT, or BLOCK", 
    )
    signal.add_argument("--reviewer-id", required=True)
    signal.add_argument("--notes", default=None)
    signal.add_argument(
        "--wait",
        action="store_true",
        help="Wait for workflow completion and print the final result as JSON",
    )

    return parser


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    attach_redaction_filter()


async def _cmd_start(case_id: str) -> WorkflowHandle:
    settings = get_settings()
    client = await connect_client()

    workflow_id = permit_case_workflow_id(case_id)
    handle = await client.start_workflow(
        PermitCaseWorkflow.run,
        PermitCaseWorkflowInput(case_id=case_id),
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )

    # Copy/paste-able correlation tuple.
    # Note: WorkflowHandle.run_id may be None when the handle targets "latest run".
    run_id = handle.first_execution_run_id or handle.run_id
    print(f"workflow_id={handle.id} run_id={run_id}")
    return handle


async def _cmd_signal_review(
    *,
    case_id: str,
    decision_outcome: str,
    reviewer_id: str,
    notes: str | None,
    wait: bool,
) -> None:
    client = await connect_client()

    workflow_id = permit_case_workflow_id(case_id)
    handle = client.get_workflow_handle(workflow_id)

    signal = ReviewDecisionSignal(
        decision_outcome=ReviewDecisionOutcome(decision_outcome),
        reviewer_id=reviewer_id,
        notes=notes,
    )
    await handle.signal(PermitCaseWorkflow.review_decision, signal)

    print(f"signaled workflow_id={workflow_id} signal=ReviewDecision")

    if wait:
        result = await handle.result()
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        else:
            payload = result
        print(json.dumps(payload, sort_keys=True))


async def _run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging()

    try:
        if args.command == "start":
            await _cmd_start(args.case_id)
            return 0

        if args.command == "signal-review":
            await _cmd_signal_review(
                case_id=args.case_id,
                decision_outcome=args.decision_outcome,
                reviewer_id=args.reviewer_id,
                notes=args.notes,
                wait=args.wait,
            )
            return 0

        raise AssertionError(f"Unhandled command: {args.command}")
    except Exception as exc:
        logger.exception("cli.error exc_type=%s", type(exc).__name__)
        return 2


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(asyncio.run(_run(argv)))


if __name__ == "__main__":
    main()
