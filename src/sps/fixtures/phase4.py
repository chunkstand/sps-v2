from __future__ import annotations

import json
import os
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sps.evidence.ids import assert_valid_evidence_id


class PortalSupportLevel(StrEnum):
    FULLY_SUPPORTED = "FULLY_SUPPORTED"
    PARTIALLY_SUPPORTED_READ_ONLY = "PARTIALLY_SUPPORTED_READ_ONLY"
    PARTIALLY_SUPPORTED_UPLOAD_ONLY = "PARTIALLY_SUPPORTED_UPLOAD_ONLY"
    UNSUPPORTED = "UNSUPPORTED"


class FreshnessState(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class ContradictionState(StrEnum):
    NONE = "NONE"
    SAME_RANK_BLOCKING = "SAME_RANK_BLOCKING"
    HIGHER_RANK_OVERRIDE = "HIGHER_RANK_OVERRIDE"
    RESOLVED = "RESOLVED"


class JurisdictionResolutionFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jurisdiction_resolution_id: str
    case_id: str
    city_authority_id: str | None = None
    county_authority_id: str | None = None
    state_authority_id: str | None = None
    utility_authority_id: str | None = None
    zoning_district: str | None = None
    overlays: list[str] | None = None
    permitting_portal_family: str | None = None
    support_level: PortalSupportLevel
    manual_requirements: list[str] | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None

    @field_validator("evidence_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: list[str]) -> list[str]:
        for item in value:
            assert_valid_evidence_id(item)
        return value


class RequirementSetFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_set_id: str
    case_id: str
    jurisdiction_ids: list[str]
    permit_types: list[str]
    forms_required: list[str]
    attachments_required: list[str]
    fee_rules: list[dict[str, Any]] | None = None
    source_rankings: list[dict[str, Any]]
    freshness_state: FreshnessState
    freshness_expires_at: datetime
    contradiction_state: ContradictionState
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None

    @field_validator("evidence_ids")
    @classmethod
    def _validate_requirement_evidence_ids(cls, value: list[str]) -> list[str]:
        for item in value:
            assert_valid_evidence_id(item)
        return value


class JurisdictionFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: datetime
    jurisdictions: list[JurisdictionResolutionFixture]


class RequirementFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: datetime
    requirement_sets: list[RequirementSetFixture]


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHASE4_FIXTURES_DIR = PROJECT_ROOT / "specs" / "sps" / "build-approved" / "fixtures" / "phase4"
JURISDICTION_FIXTURE_PATH = PHASE4_FIXTURES_DIR / "jurisdiction.json"
REQUIREMENTS_FIXTURE_PATH = PHASE4_FIXTURES_DIR / "requirements.json"
PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV = "SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE"

FixtureModel = TypeVar("FixtureModel", bound=BaseModel)


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jurisdiction_fixtures(path: Path | None = None) -> JurisdictionFixtureDataset:
    fixture_path = path or JURISDICTION_FIXTURE_PATH
    payload = _load_fixture(fixture_path)
    try:
        return JurisdictionFixtureDataset.model_validate(payload)
    except Exception as exc:  # pragma: no cover - rich error context
        raise ValueError(f"Jurisdiction fixture validation failed for {fixture_path}") from exc


def load_requirement_fixtures(path: Path | None = None) -> RequirementFixtureDataset:
    fixture_path = path or REQUIREMENTS_FIXTURE_PATH
    payload = _load_fixture(fixture_path)
    try:
        return RequirementFixtureDataset.model_validate(payload)
    except Exception as exc:  # pragma: no cover - rich error context
        raise ValueError(f"Requirement fixture validation failed for {fixture_path}") from exc


def load_phase4_fixtures() -> tuple[JurisdictionFixtureDataset, RequirementFixtureDataset]:
    return load_jurisdiction_fixtures(), load_requirement_fixtures()


def resolve_phase4_fixture_case_id(case_id: str) -> str:
    override = os.getenv(PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV)
    if override:
        override = override.strip()
    return override or case_id


def _rewrite_case_id(fixtures: list[FixtureModel], runtime_case_id: str) -> list[FixtureModel]:
    return [fixture.model_copy(update={"case_id": runtime_case_id}) for fixture in fixtures]


def select_jurisdiction_fixtures(
    case_id: str,
) -> tuple[list[JurisdictionResolutionFixture], str]:
    fixture_case_id = resolve_phase4_fixture_case_id(case_id)
    dataset = load_jurisdiction_fixtures()
    fixtures = [fixture for fixture in dataset.jurisdictions if fixture.case_id == fixture_case_id]
    return _rewrite_case_id(fixtures, case_id), fixture_case_id


def select_requirement_fixtures(
    case_id: str,
) -> tuple[list[RequirementSetFixture], str]:
    fixture_case_id = resolve_phase4_fixture_case_id(case_id)
    dataset = load_requirement_fixtures()
    fixtures = [fixture for fixture in dataset.requirement_sets if fixture.case_id == fixture_case_id]
    return _rewrite_case_id(fixtures, case_id), fixture_case_id
