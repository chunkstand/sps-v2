"""Pytest configuration for integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.fixtures.seed_submission_package import seed_submission_attempt


@pytest.fixture
def seed_fixtures(db_session: Session):
    """Helper to seed minimal fixtures including SubmissionAttempt."""
    def _seed(case_id: str, submission_attempt_id: str, attempt_number: int = 1, status: str = "SUBMITTED"):
        return seed_submission_attempt(db_session, case_id, submission_attempt_id, attempt_number, status)
    return _seed
