from __future__ import annotations

import os

from sps.adapters import get_runtime_adapter_versions, get_runtime_adapters


def test_city_portal_family_a_slice_uses_real_adapters() -> None:
    case_id = "CASE-CITYA-MANUAL-001"
    adapters = get_runtime_adapters()

    jurisdiction = adapters.load_jurisdiction(case_id)
    requirements = adapters.load_requirements(case_id)
    compliance = adapters.load_compliance(case_id)
    documents = adapters.load_documents(case_id)
    submission = adapters.load_submission_plan(
        case_id,
        target_portal_family="CITY_PORTAL_FAMILY_A",
    )
    status_mapping = adapters.load_status_mapping(case_id)

    assert jurisdiction.source_kind == "city_portal_family_a"
    assert jurisdiction.source_key == case_id
    assert jurisdiction.value[0].permitting_portal_family == "CITY_PORTAL_FAMILY_A"

    assert requirements.source_kind == "city_portal_family_a"
    assert requirements.value[0].attachments_required

    assert compliance.source_kind == "city_portal_family_a"
    assert compliance.value[0].warnings

    assert documents.source_kind == "city_portal_family_a"
    assert len(documents.value.documents) == 2
    assert all(spec.template_path.exists() for spec in documents.value.documents)

    assert submission.source_kind == "city_portal_family_a"
    assert submission.value is not None
    assert submission.value.channel_type == "official_authority_email"

    assert status_mapping.source_kind == "city_portal_family_a"
    assert status_mapping.value.mapping_version == "2026-03-17.1"
    assert "Resubmission Required" in status_mapping.value.mappings
    assert "Final Approval" in status_mapping.value.mappings


def test_non_selected_cases_fall_back_to_fixture_adapters() -> None:
    original_phase4 = os.environ.get("SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE")
    original_phase5 = os.environ.get("SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE")
    original_phase6 = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    original_phase7 = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"

        case_id = "CASE-RUNTIME-FALLBACK-001"
        adapters = get_runtime_adapters()

        jurisdiction = adapters.load_jurisdiction(case_id)
        requirements = adapters.load_requirements(case_id)
        compliance = adapters.load_compliance(case_id)
        documents = adapters.load_documents(case_id)
        submission = adapters.load_submission_plan(
            case_id,
            target_portal_family="CITY_PORTAL_FAMILY_A",
        )
        status_mapping = adapters.load_status_mapping(case_id)

        assert jurisdiction.source_kind == "fixture"
        assert jurisdiction.source_key == "CASE-EXAMPLE-001"
        assert all(record.case_id == case_id for record in jurisdiction.value)

        assert requirements.source_kind == "fixture"
        assert requirements.source_key == "CASE-EXAMPLE-001"
        assert all(record.case_id == case_id for record in requirements.value)

        assert compliance.source_kind == "fixture"
        assert compliance.source_key == "CASE-EXAMPLE-001"
        assert all(record.case_id == case_id for record in compliance.value)

        assert documents.source_kind == "fixture"
        assert documents.source_key == "CASE-EXAMPLE-001"
        assert documents.value.documents
        assert documents.value.case_id == case_id

        assert submission.source_kind == "fixture"
        assert submission.source_key == "CASE-EXAMPLE-001"
        assert submission.value is not None
        assert submission.value.case_id == case_id

        assert status_mapping.source_kind == "fixture"
        assert status_mapping.source_key == "CASE-EXAMPLE-001"
        assert "Approved" in status_mapping.value.mappings
    finally:
        if original_phase4 is not None:
            os.environ["SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE"] = original_phase4
        else:
            os.environ.pop("SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase5 is not None:
            os.environ["SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE"] = original_phase5
        else:
            os.environ.pop("SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase6 is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original_phase6
        else:
            os.environ.pop("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase7 is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_phase7
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)


def test_phaniville_manual_slice_uses_real_adapters() -> None:
    case_id = "CASE-PHANI-MANUAL-001"
    adapters = get_runtime_adapters()

    jurisdiction = adapters.load_jurisdiction(case_id)
    requirements = adapters.load_requirements(case_id)
    compliance = adapters.load_compliance(case_id)
    documents = adapters.load_documents(case_id)
    submission = adapters.load_submission_plan(
        case_id,
        target_portal_family="PHANIVILLE_MANUAL_PORTAL",
    )
    status_mapping = adapters.load_status_mapping(case_id)

    assert jurisdiction.source_kind == "phaniville_manual"
    assert jurisdiction.source_key == case_id
    assert jurisdiction.value[0].permitting_portal_family == "PHANIVILLE_MANUAL_PORTAL"

    assert requirements.source_kind == "phaniville_manual"
    assert "SitePlan-PHANI" in requirements.value[0].attachments_required

    assert compliance.source_kind == "phaniville_manual"
    assert compliance.value[0].warnings

    assert documents.source_kind == "phaniville_manual"
    assert len(documents.value.documents) == 2
    assert all(spec.template_path.exists() for spec in documents.value.documents)

    assert submission.source_kind == "phaniville_manual"
    assert submission.value is not None
    assert submission.value.channel_type == "counter_dropoff"

    assert status_mapping.source_kind == "phaniville_manual"
    assert "Packet Accepted" in status_mapping.value.mappings
    assert "Issued Final" in status_mapping.value.mappings


def test_runtime_adapter_versions_surface_all_concrete_slices() -> None:
    versions = get_runtime_adapter_versions()

    assert versions["city_portal_family_a"] == "2026-03-17.1"
    assert versions["phaniville_manual"] == "2026-03-17.1"
