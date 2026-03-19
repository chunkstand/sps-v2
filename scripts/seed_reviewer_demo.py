from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from alembic import command
from alembic.config import Config

from sps.db.models import EvidenceArtifact, JurisdictionResolution, PermitCase, Project, ReviewDecision
from sps.db.session import get_sessionmaker


@dataclass(frozen=True)
class DemoCaseSpec:
    case_id: str
    project_id: str
    artifact_id: str
    resolution_id: str
    decision_id: str | None
    address: str
    parcel_id: str
    project_type: str
    system_size_kw: float
    battery_flag: bool
    service_upgrade_flag: bool
    trenching_flag: bool
    structural_modification_flag: bool
    roof_type: str
    occupancy_classification: str
    utility_name: str
    submission_mode: str
    portal_support_level: str
    created_at: dt.datetime
    notes: str


DEMO_CASES: tuple[DemoCaseSpec, ...] = (
    DemoCaseSpec(
        case_id="CASE-DEMO-REVIEW-001",
        project_id="PROJ-DEMO-REVIEW-001",
        artifact_id="ART-DEMO-REVIEW-001",
        resolution_id="JURIS-DEMO-REVIEW-001",
        decision_id="DEC-DEMO-REVIEW-001",
        address="123 Mesa View Dr, Denver, CO 80211",
        parcel_id="02918-11-004-000",
        project_type="SOLAR",
        system_size_kw=7.2,
        battery_flag=False,
        service_upgrade_flag=False,
        trenching_flag=False,
        structural_modification_flag=False,
        roof_type="COMP_SHINGLE",
        occupancy_classification="R-3",
        utility_name="Xcel Energy",
        submission_mode="AUTOMATED",
        portal_support_level="FULLY_SUPPORTED",
        created_at=dt.datetime(2026, 3, 16, 15, 30, tzinfo=dt.UTC),
        notes="Initial jurisdiction packet is ready for review.",
    ),
    DemoCaseSpec(
        case_id="CASE-DEMO-REVIEW-002",
        project_id="PROJ-DEMO-REVIEW-002",
        artifact_id="ART-DEMO-REVIEW-002",
        resolution_id="JURIS-DEMO-REVIEW-002",
        decision_id=None,
        address="48 Juniper Ridge Rd, Boulder, CO 80302",
        parcel_id="14612-08-021-000",
        project_type="SOLAR_PLUS_STORAGE",
        system_size_kw=10.8,
        battery_flag=True,
        service_upgrade_flag=True,
        trenching_flag=False,
        structural_modification_flag=False,
        roof_type="STANDING_SEAM",
        occupancy_classification="R-3",
        utility_name="Boulder Electric",
        submission_mode="AUTOMATED",
        portal_support_level="PARTIALLY_SUPPORTED",
        created_at=dt.datetime(2026, 3, 17, 9, 0, tzinfo=dt.UTC),
        notes="Support level review is pending before package sealing.",
    ),
    DemoCaseSpec(
        case_id="CASE-DEMO-REVIEW-003",
        project_id="PROJ-DEMO-REVIEW-003",
        artifact_id="ART-DEMO-REVIEW-003",
        resolution_id="JURIS-DEMO-REVIEW-003",
        decision_id="DEC-DEMO-REVIEW-003",
        address="900 Canyon Creek Ln, Fort Collins, CO 80524",
        parcel_id="97011-14-112-000",
        project_type="GROUND_MOUNT",
        system_size_kw=18.4,
        battery_flag=False,
        service_upgrade_flag=False,
        trenching_flag=True,
        structural_modification_flag=True,
        roof_type="N/A",
        occupancy_classification="U",
        utility_name="Poudre Valley REA",
        submission_mode="MANUAL_FALLBACK_READY",
        portal_support_level="LIMITED_SUPPORT",
        created_at=dt.datetime(2026, 3, 18, 7, 45, tzinfo=dt.UTC),
        notes="Previous review blocked on site-plan detail; updated evidence is ready.",
    ),
)


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _upsert_case(spec: DemoCaseSpec) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        permit_case = session.get(PermitCase, spec.case_id)
        if permit_case is None:
            permit_case = PermitCase(case_id=spec.case_id)
            session.add(permit_case)

        permit_case.tenant_id = "tenant-demo"
        permit_case.project_id = spec.project_id
        permit_case.case_state = "REVIEW_PENDING"
        permit_case.review_state = "PENDING"
        permit_case.submission_mode = spec.submission_mode
        permit_case.portal_support_level = spec.portal_support_level
        permit_case.current_package_id = None
        permit_case.current_release_profile = "default"
        permit_case.legal_hold = False
        permit_case.closure_reason = None
        permit_case.created_at = spec.created_at
        permit_case.updated_at = spec.created_at
        session.flush()

        project = session.get(Project, spec.project_id)
        if project is None:
            project = Project(project_id=spec.project_id, case_id=spec.case_id)
            session.add(project)

        project.case_id = spec.case_id
        project.address = spec.address
        project.parcel_id = spec.parcel_id
        project.project_type = spec.project_type
        project.system_size_kw = spec.system_size_kw
        project.battery_flag = spec.battery_flag
        project.service_upgrade_flag = spec.service_upgrade_flag
        project.trenching_flag = spec.trenching_flag
        project.structural_modification_flag = spec.structural_modification_flag
        project.roof_type = spec.roof_type
        project.occupancy_classification = spec.occupancy_classification
        project.utility_name = spec.utility_name
        project.contact_metadata = {
            "owner_name": "Demo Homeowner",
            "email": "review-demo@example.com",
            "notes": spec.notes,
        }
        project.created_at = spec.created_at
        project.updated_at = spec.created_at
        session.flush()

        artifact = session.get(EvidenceArtifact, spec.artifact_id)
        if artifact is None:
            artifact = EvidenceArtifact(artifact_id=spec.artifact_id)
            session.add(artifact)

        artifact.artifact_class = "JURISDICTION_PACKET"
        artifact.producing_service = "reviewer-demo-seed"
        artifact.linked_case_id = spec.case_id
        artifact.linked_object_id = spec.resolution_id
        artifact.authoritativeness = "ADVISORY"
        artifact.retention_class = "CASE_CORE_7Y"
        artifact.checksum = (spec.artifact_id.replace("-", "").lower() * 8)[:64]
        artifact.storage_uri = f"s3://sps-evidence/demo/{spec.artifact_id}.json"
        artifact.content_bytes = 2048
        artifact.content_type = "application/json"
        artifact.provenance = {
            "seed": "reviewer_demo",
            "summary": spec.notes,
            "utility_name": spec.utility_name,
        }
        artifact.created_at = spec.created_at
        artifact.expires_at = None
        artifact.legal_hold_flag = False

        resolution = session.get(JurisdictionResolution, spec.resolution_id)
        if resolution is None:
            resolution = JurisdictionResolution(
                jurisdiction_resolution_id=spec.resolution_id,
                case_id=spec.case_id,
            )
            session.add(resolution)

        resolution.case_id = spec.case_id
        resolution.city_authority_id = f"CITY-{spec.case_id}"
        resolution.county_authority_id = f"COUNTY-{spec.case_id}"
        resolution.state_authority_id = "CO-STATE"
        resolution.utility_authority_id = f"UTILITY-{spec.case_id}"
        resolution.zoning_district = "RES-SOLAR"
        resolution.overlays = ["WUI_CHECK"] if spec.structural_modification_flag else []
        resolution.permitting_portal_family = "CITY_PORTAL_FAMILY_A"
        resolution.support_level = spec.portal_support_level
        resolution.manual_requirements = (
            ["wet-stamped structural letter"]
            if spec.structural_modification_flag
            else ["utility disconnect photo"]
        )
        resolution.evidence_ids = [spec.artifact_id]
        resolution.provenance = {
            "seed": "reviewer_demo",
            "review_surface": "jurisdiction",
        }
        resolution.evidence_payload = {
            "address": spec.address,
            "utility_name": spec.utility_name,
            "notes": spec.notes,
        }
        resolution.created_at = spec.created_at
        resolution.updated_at = spec.created_at

        if spec.decision_id is not None:
            decision = session.get(ReviewDecision, spec.decision_id)
            if decision is None:
                decision = ReviewDecision(decision_id=spec.decision_id)
                session.add(decision)

            decision.schema_version = "1.0.0"
            decision.case_id = spec.case_id
            decision.object_type = "JurisdictionResolution"
            decision.object_id = spec.resolution_id
            decision.decision_outcome = "BLOCK"
            decision.reviewer_id = "reviewer-demo"
            decision.subject_author_id = "planner-demo"
            decision.reviewer_independence_status = "PASS"
            decision.evidence_ids = [spec.artifact_id]
            decision.contradiction_resolution = None
            decision.dissent_flag = False
            decision.notes = spec.notes
            decision.decision_at = spec.created_at + dt.timedelta(hours=2)
            decision.idempotency_key = f"idem/{spec.decision_id}"
            decision.created_at = spec.created_at + dt.timedelta(hours=2)

        session.commit()


def main() -> None:
    _migrate_db()
    for spec in DEMO_CASES:
        _upsert_case(spec)

    print("Seeded reviewer demo cases:")
    for spec in DEMO_CASES:
        print(f"- {spec.case_id} :: {spec.address}")
    print("Use /reviewer with X-Reviewer-Api-Key=dev-reviewer-key to load the queue.")


if __name__ == "__main__":
    main()
