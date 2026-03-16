from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHASE7_FIXTURES_DIR = PROJECT_ROOT / "specs" / "sps" / "build-approved" / "fixtures" / "phase7"
SUBMISSION_ADAPTER_FIXTURE_PATH = PHASE7_FIXTURES_DIR / "submission_adapter.json"
PHASE7_FIXTURE_CASE_ID_OVERRIDE_ENV = "SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"

FixtureModel = TypeVar("FixtureModel", bound=BaseModel)


class SubmissionAdapterFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    target_portal_family: str
    portal_support_level: str
    channel_type: str
    reason: str | None = None
    operator_instructions: list[str] = Field(default_factory=list)
    required_proof_types: list[str] = Field(default_factory=list)
    required_attachment_sources: list[str] = Field(default_factory=list)
    escalation_owner: str | None = None


class SubmissionAdapterFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: datetime
    adapter_inputs: list[SubmissionAdapterFixture]


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_submission_adapter_fixtures(
    path: Path | None = None,
) -> SubmissionAdapterFixtureDataset:
    fixture_path = path or SUBMISSION_ADAPTER_FIXTURE_PATH
    payload = _load_fixture(fixture_path)
    try:
        return SubmissionAdapterFixtureDataset.model_validate(payload)
    except Exception as exc:  # pragma: no cover - rich error context
        raise ValueError(f"Submission adapter fixture validation failed for {fixture_path}") from exc


def resolve_phase7_fixture_case_id(case_id: str) -> str:
    override = os.getenv(PHASE7_FIXTURE_CASE_ID_OVERRIDE_ENV)
    if override:
        override = override.strip()
    return override or case_id


def _rewrite_case_id(fixtures: list[FixtureModel], runtime_case_id: str) -> list[FixtureModel]:
    return [fixture.model_copy(update={"case_id": runtime_case_id}) for fixture in fixtures]


def select_submission_adapter_fixtures(case_id: str) -> tuple[list[SubmissionAdapterFixture], str]:
    fixture_case_id = resolve_phase7_fixture_case_id(case_id)
    dataset = load_submission_adapter_fixtures()
    fixtures = [fixture for fixture in dataset.adapter_inputs if fixture.case_id == fixture_case_id]
    return _rewrite_case_id(fixtures, case_id), fixture_case_id
