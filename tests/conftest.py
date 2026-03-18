"""Pytest marker defaults and shared test fixtures."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.fixtures.seed_submission_package import seed_submission_attempt


@pytest.fixture
def seed_fixtures(db_session: Session):
    """Helper to seed minimal fixtures including SubmissionAttempt."""

    def _seed(
        case_id: str, submission_attempt_id: str, attempt_number: int = 1, status: str = "SUBMITTED"
    ):
        return seed_submission_attempt(
            db_session, case_id, submission_attempt_id, attempt_number, status
        )

    return _seed

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker("integration") or item.get_closest_marker("unit"):
            continue
        item.add_marker(pytest.mark.unit)
