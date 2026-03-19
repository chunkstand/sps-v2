from __future__ import annotations

import pytest

from sps.workflows.cli import _build_parser


def test_signal_review_parser_requires_decision_id() -> None:
    parser = _build_parser()

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(
            [
                "signal-review",
                "--case-id",
                "CASE-001",
                "--decision-outcome",
                "ACCEPT",
                "--reviewer-id",
                "reviewer-1",
            ]
        )

    assert excinfo.value.code == 2


def test_signal_review_parser_accepts_decision_id() -> None:
    parser = _build_parser()

    args = parser.parse_args(
        [
            "signal-review",
            "--case-id",
            "CASE-001",
            "--decision-id",
            "DEC-001",
            "--decision-outcome",
            "ACCEPT",
            "--reviewer-id",
            "reviewer-1",
        ]
    )

    assert args.command == "signal-review"
    assert args.case_id == "CASE-001"
    assert args.decision_id == "DEC-001"
