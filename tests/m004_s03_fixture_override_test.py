"""M004 / S03 fixture override selection tests."""

from __future__ import annotations

import pytest

from sps.fixtures.phase4 import (
    PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV,
    load_jurisdiction_fixtures,
    load_requirement_fixtures,
    select_jurisdiction_fixtures,
    select_requirement_fixtures,
)


@pytest.mark.usefixtures("monkeypatch")
def test_fixture_override_rewrites_case_id(monkeypatch: pytest.MonkeyPatch) -> None:
    jurisdiction_dataset = load_jurisdiction_fixtures()
    requirement_dataset = load_requirement_fixtures()

    fixture_case_id = jurisdiction_dataset.jurisdictions[0].case_id
    assert fixture_case_id == requirement_dataset.requirement_sets[0].case_id

    runtime_case_id = f"CASE-RUNTIME-{fixture_case_id}"
    monkeypatch.setenv(PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV, fixture_case_id)

    jurisdiction_fixtures, jurisdiction_lookup_id = select_jurisdiction_fixtures(runtime_case_id)
    requirement_fixtures, requirement_lookup_id = select_requirement_fixtures(runtime_case_id)

    assert jurisdiction_lookup_id == fixture_case_id
    assert requirement_lookup_id == fixture_case_id
    assert jurisdiction_fixtures
    assert requirement_fixtures
    assert all(fixture.case_id == runtime_case_id for fixture in jurisdiction_fixtures)
    assert all(fixture.case_id == runtime_case_id for fixture in requirement_fixtures)


def test_fixture_override_defaults_to_runtime_case_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PHASE4_FIXTURE_CASE_ID_OVERRIDE_ENV, raising=False)

    jurisdiction_dataset = load_jurisdiction_fixtures()
    requirement_dataset = load_requirement_fixtures()

    runtime_case_id = jurisdiction_dataset.jurisdictions[0].case_id
    assert runtime_case_id == requirement_dataset.requirement_sets[0].case_id

    jurisdiction_fixtures, jurisdiction_lookup_id = select_jurisdiction_fixtures(runtime_case_id)
    requirement_fixtures, requirement_lookup_id = select_requirement_fixtures(runtime_case_id)

    assert jurisdiction_lookup_id == runtime_case_id
    assert requirement_lookup_id == runtime_case_id
    assert jurisdiction_fixtures
    assert requirement_fixtures
    assert all(fixture.case_id == runtime_case_id for fixture in jurisdiction_fixtures)
    assert all(fixture.case_id == runtime_case_id for fixture in requirement_fixtures)
