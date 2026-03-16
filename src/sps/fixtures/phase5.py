from __future__ import annotations

import json
import os
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHASE5_FIXTURES_DIR = PROJECT_ROOT / "specs" / "sps" / "build-approved" / "fixtures" / "phase5"
COMPLIANCE_FIXTURE_PATH = PHASE5_FIXTURES_DIR / "compliance.json"
INCENTIVES_FIXTURE_PATH = PHASE5_FIXTURES_DIR / "incentives.json"
PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV = "SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE"

FixtureModel = TypeVar("FixtureModel", bound=BaseModel)


class ComplianceRuleOutcome(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


class ComplianceRuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    outcome: ComplianceRuleOutcome
    summary: str | None = None
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class ComplianceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    rule_id: str
    summary: str
    recommendation: str | None = None
    provenance: dict[str, Any] | None = None


class ComplianceEvaluationFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compliance_evaluation_id: str
    case_id: str
    schema_version: str
    evaluated_at: datetime
    rule_results: list[ComplianceRuleResult]
    blockers: list[ComplianceIssue] = Field(default_factory=list)
    warnings: list[ComplianceIssue] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class ComplianceFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: datetime
    evaluations: list[ComplianceEvaluationFixture]


class IncentiveProgramCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    program_name: str
    program_type: str
    eligibility_status: str
    estimated_value_usd: float | None = None
    source_id: str
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class IncentiveDeadline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deadline_id: str
    due_at: datetime
    summary: str
    source_id: str
    provenance: dict[str, Any] | None = None


class IncentiveAssessmentFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incentive_assessment_id: str
    case_id: str
    schema_version: str
    assessed_at: datetime
    candidate_programs: list[IncentiveProgramCandidate]
    eligibility_status: str
    stacking_conflicts: list[str] = Field(default_factory=list)
    deadlines: list[IncentiveDeadline] = Field(default_factory=list)
    source_ids: list[str]
    advisory_value_range: str | None = None
    authoritative_value_state: str
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class IncentiveFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: datetime
    assessments: list[IncentiveAssessmentFixture]


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_compliance_fixtures(path: Path | None = None) -> ComplianceFixtureDataset:
    fixture_path = path or COMPLIANCE_FIXTURE_PATH
    payload = _load_fixture(fixture_path)
    try:
        return ComplianceFixtureDataset.model_validate(payload)
    except Exception as exc:  # pragma: no cover - rich error context
        raise ValueError(f"Compliance fixture validation failed for {fixture_path}") from exc


def load_incentive_fixtures(path: Path | None = None) -> IncentiveFixtureDataset:
    fixture_path = path or INCENTIVES_FIXTURE_PATH
    payload = _load_fixture(fixture_path)
    try:
        return IncentiveFixtureDataset.model_validate(payload)
    except Exception as exc:  # pragma: no cover - rich error context
        raise ValueError(f"Incentive fixture validation failed for {fixture_path}") from exc


def load_phase5_fixtures() -> ComplianceFixtureDataset:
    return load_compliance_fixtures()


def resolve_phase5_fixture_case_id(case_id: str) -> str:
    override = os.getenv(PHASE5_FIXTURE_CASE_ID_OVERRIDE_ENV)
    if override:
        override = override.strip()
    return override or case_id


def _rewrite_case_id(fixtures: list[FixtureModel], runtime_case_id: str) -> list[FixtureModel]:
    return [fixture.model_copy(update={"case_id": runtime_case_id}) for fixture in fixtures]


def select_compliance_fixtures(case_id: str) -> tuple[list[ComplianceEvaluationFixture], str]:
    fixture_case_id = resolve_phase5_fixture_case_id(case_id)
    dataset = load_compliance_fixtures()
    fixtures = [fixture for fixture in dataset.evaluations if fixture.case_id == fixture_case_id]
    return _rewrite_case_id(fixtures, case_id), fixture_case_id


def select_incentive_fixtures(case_id: str) -> tuple[list[IncentiveAssessmentFixture], str]:
    fixture_case_id = resolve_phase5_fixture_case_id(case_id)
    dataset = load_incentive_fixtures()
    fixtures = [fixture for fixture in dataset.assessments if fixture.case_id == fixture_case_id]
    return _rewrite_case_id(fixtures, case_id), fixture_case_id
