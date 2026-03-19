from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.exc import IntegrityError
from temporalio import activity

from sps.adapters import get_runtime_adapters
from sps.audit.events import emit_audit_event
from sps.db.models import (
    ApprovalRecord,
    CaseTransitionLedger,
    ComplianceEvaluation,
    ContradictionArtifact,
    CorrectionTask,
    OverrideArtifact,
    DocumentArtifact,
    EmergencyRecord,
    EvidenceArtifact,
    ExternalStatusEvent,
    IncentiveAssessment,
    InspectionMilestone,
    JurisdictionResolution,
    ManualFallbackPackage,
    PermitCase,
    Project,
    RequirementSet,
    ResubmissionPackage,
    ReviewDecision,
    SubmissionAttempt,
    SubmissionPackage,
)
from sps.db.session import get_sessionmaker
from sps.failpoints import FailpointFired, fail_once
from sps.fixtures.phase5 import select_incentive_fixtures
from sps.guards.guard_assertions import get_normalized_business_invariants
from sps.workflows.permit_case.contracts import (
    AppliedStateTransitionResult,
    CaseState,
    DeniedStateTransitionResult,
    ExternalStatusClass,
    ExternalStatusConfidence,
    ExternalStatusNormalizationRequest,
    ExternalStatusNormalizationResult,
    PermitCaseStateSnapshot,
    PersistApprovalRecordRequest,
    PersistComplianceEvaluationRequest,
    PersistCorrectionTaskRequest,
    PersistIncentiveAssessmentRequest,
    PersistInspectionMilestoneRequest,
    PersistJurisdictionResolutionRequest,
    PersistRequirementSetRequest,
    PersistResubmissionPackageRequest,
    PersistReviewDecisionRequest,
    PersistSubmissionPackageRequest,
    SubmissionAdapterOutcome,
    SubmissionAdapterRequest,
    SubmissionAdapterResult,
    StateTransitionRequest,
    StateTransitionResult,
    parse_state_transition_result,
)

logger = logging.getLogger(__name__)


@activity.defn
def ensure_permit_case_exists(case_id: str) -> bool:
    """Ensure a minimal `permit_cases` row exists.

    This proves the determinism boundary: all DB I/O happens in an activity, not
    in workflow code.

    Returns:
        True if the row was created, False if it already existed.
    """

    info = activity.info()
    logger.info(
        "activity.start name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s",
        info.workflow_id,
        info.workflow_run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    created = False

    try:
        with SessionLocal() as session:
            existing = session.get(PermitCase, case_id)
            if existing is None:
                created = True
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-local",
                        project_id=f"project-{case_id}",
                        # Contract-valid seed: the workflow proof path starts at REVIEW_PENDING.
                        case_state=CaseState.REVIEW_PENDING.value,
                        review_state="PENDING",
                        submission_mode="AUTOMATED",
                        portal_support_level="FULLY_SUPPORTED",
                        current_package_id=None,
                        current_release_profile="default",
                        legal_hold=False,
                        closure_reason=None,
                    )
                )
                session.commit()

        logger.info(
            "activity.ok name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s created=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            created,
        )
        return created
    except Exception as exc:
        # Temporal will record the exception; this log line provides a grep-able correlation tuple.
        logger.exception(
            "activity.error name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def fetch_permit_case_state(case_id: str) -> PermitCaseStateSnapshot:
    """Fetch the current PermitCase state for workflow branching."""

    workflow_id, run_id = _safe_temporal_ids()
    logger.info(
        "activity.start name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s",
        workflow_id,
        run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            if case is None:
                raise LookupError(f"permit_cases row not found for case_id={case_id}")

            snapshot = PermitCaseStateSnapshot(
                case_id=case.case_id,
                case_state=CaseState(case.case_state),
                project_id=case.project_id,
            )

        logger.info(
            "activity.ok name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s case_state=%s",
            workflow_id,
            run_id,
            case_id,
            snapshot.case_state,
        )
        return snapshot
    except Exception as exc:
        logger.exception(
            "activity.error name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            workflow_id,
            run_id,
            case_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def validate_emergency_artifact(emergency_id: str) -> str:
    """Ensure the EmergencyRecord exists and has not expired."""
    workflow_id, run_id = _safe_temporal_ids()
    logger.info(
        "activity.start name=validate_emergency_artifact workflow_id=%s run_id=%s emergency_id=%s",
        workflow_id,
        run_id,
        emergency_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            record = session.get(EmergencyRecord, emergency_id)
            if record is None:
                raise LookupError(f"emergency_records row not found for emergency_id={emergency_id}")

            expires_at = record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.UTC)

            if expires_at <= dt.datetime.now(dt.UTC):
                raise ValueError(f"emergency_id={emergency_id} expired at {expires_at.isoformat()}")

        logger.info(
            "activity.ok name=validate_emergency_artifact workflow_id=%s run_id=%s emergency_id=%s",
            workflow_id,
            run_id,
            emergency_id,
        )
        return emergency_id
    except Exception as exc:
        logger.exception(
            "activity.error name=validate_emergency_artifact workflow_id=%s run_id=%s emergency_id=%s exc_type=%s",
            workflow_id,
            run_id,
            emergency_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def validate_reviewer_confirmation(reviewer_confirmation_id: str) -> str:
    """Ensure the ReviewDecision exists for emergency hold exit confirmation."""
    workflow_id, run_id = _safe_temporal_ids()
    logger.info(
        "activity.start name=validate_reviewer_confirmation workflow_id=%s run_id=%s reviewer_confirmation_id=%s",
        workflow_id,
        run_id,
        reviewer_confirmation_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            decision = session.get(ReviewDecision, reviewer_confirmation_id)
            if decision is None:
                raise LookupError(
                    "review_decisions row not found for reviewer_confirmation_id=%s" % reviewer_confirmation_id
                )

        logger.info(
            "activity.ok name=validate_reviewer_confirmation workflow_id=%s run_id=%s reviewer_confirmation_id=%s",
            workflow_id,
            run_id,
            reviewer_confirmation_id,
        )
        return reviewer_confirmation_id
    except Exception as exc:
        logger.exception(
            "activity.error name=validate_reviewer_confirmation workflow_id=%s run_id=%s reviewer_confirmation_id=%s exc_type=%s",
            workflow_id,
            run_id,
            reviewer_confirmation_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_jurisdiction_resolutions(
    request: PersistJurisdictionResolutionRequest | dict,
) -> list[str]:
    """Persist jurisdiction resolution fixtures for a case idempotently."""

    req = PersistJurisdictionResolutionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    adapter_result = get_runtime_adapters().load_jurisdiction(req.case_id)
    records = adapter_result.value
    source_case_id = adapter_result.source_key
    logger.info(
        "activity.lookup name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        adapter_result.source_kind,
        source_case_id,
        1 if source_case_id != req.case_id else 0,
    )
    if not records:
        raise LookupError(
            "no jurisdiction adapter data found for case_id=%s source_case_id=%s"
            % (req.case_id, source_case_id)
        )

    SessionLocal = get_sessionmaker()
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for record in records:
                        existing = session.get(JurisdictionResolution, record.jurisdiction_resolution_id)
                        if existing is None:
                            session.add(
                                JurisdictionResolution(
                                    jurisdiction_resolution_id=record.jurisdiction_resolution_id,
                                    case_id=record.case_id,
                                    city_authority_id=record.city_authority_id,
                                    county_authority_id=record.county_authority_id,
                                    state_authority_id=record.state_authority_id,
                                    utility_authority_id=record.utility_authority_id,
                                    zoning_district=record.zoning_district,
                                    overlays=record.overlays,
                                    permitting_portal_family=record.permitting_portal_family,
                                    support_level=str(record.support_level),
                                    manual_requirements=record.manual_requirements,
                                    evidence_ids=record.evidence_ids,
                                    provenance=record.provenance,
                                    evidence_payload=record.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(record.jurisdiction_resolution_id)

                logger.info(
                    "jurisdiction_activity.persisted workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    adapter_result.source_kind,
                    source_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )

                logger.info(
                    "activity.ok name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s source_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    source_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(JurisdictionResolution)
                .filter(JurisdictionResolution.case_id == req.case_id)
                .all()
            )
            existing_ids = [row.jurisdiction_resolution_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    f"jurisdiction_resolutions insert raced but rows not found for case_id={req.case_id}"
                )

            logger.info(
                "jurisdiction_activity.persisted workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                adapter_result.source_kind,
                source_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s source_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                source_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_requirement_sets(request: PersistRequirementSetRequest | dict) -> list[str]:
    """Persist requirement set fixtures for a case idempotently."""

    req = PersistRequirementSetRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    adapter_result = get_runtime_adapters().load_requirements(req.case_id)
    records = adapter_result.value
    source_case_id = adapter_result.source_key
    logger.info(
        "activity.lookup name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        adapter_result.source_kind,
        source_case_id,
        1 if source_case_id != req.case_id else 0,
    )
    if not records:
        raise LookupError(
            "no requirement adapter data found for case_id=%s source_case_id=%s"
            % (req.case_id, source_case_id)
        )

    SessionLocal = get_sessionmaker()
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for record in records:
                        existing = session.get(RequirementSet, record.requirement_set_id)
                        if existing is None:
                            freshness_expires_at = record.freshness_expires_at
                            if freshness_expires_at.tzinfo is None:
                                freshness_expires_at = freshness_expires_at.replace(tzinfo=dt.UTC)

                            session.add(
                                RequirementSet(
                                    requirement_set_id=record.requirement_set_id,
                                    case_id=record.case_id,
                                    jurisdiction_ids=record.jurisdiction_ids,
                                    permit_types=record.permit_types,
                                    forms_required=record.forms_required,
                                    attachments_required=record.attachments_required,
                                    fee_rules=record.fee_rules,
                                    source_rankings=record.source_rankings,
                                    freshness_state=str(record.freshness_state),
                                    freshness_expires_at=freshness_expires_at,
                                    contradiction_state=str(record.contradiction_state),
                                    evidence_ids=record.evidence_ids,
                                    provenance=record.provenance,
                                    evidence_payload=record.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(record.requirement_set_id)

                logger.info(
                    "requirements_activity.persisted workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    adapter_result.source_kind,
                    source_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )

                logger.info(
                    "activity.ok name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s source_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    source_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(RequirementSet)
                .filter(RequirementSet.case_id == req.case_id)
                .all()
            )
            existing_ids = [row.requirement_set_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    f"requirement_sets insert raced but rows not found for case_id={req.case_id}"
                )

            logger.info(
                "requirements_activity.persisted workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                adapter_result.source_kind,
                source_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s source_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                source_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_compliance_evaluation(
    request: PersistComplianceEvaluationRequest | dict,
) -> list[str]:
    """Persist compliance evaluation fixtures for a case idempotently."""

    req = PersistComplianceEvaluationRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    adapter_result = get_runtime_adapters().load_compliance(req.case_id)
    records = adapter_result.value
    source_case_id = adapter_result.source_key
    logger.info(
        "activity.lookup name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        adapter_result.source_kind,
        source_case_id,
        1 if source_case_id != req.case_id else 0,
    )
    if not records:
        raise LookupError(
            "no compliance adapter data found for case_id=%s source_case_id=%s"
            % (req.case_id, source_case_id)
        )

    SessionLocal = get_sessionmaker()
    fixture_ids = [record.compliance_evaluation_id for record in records]
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for record in records:
                        existing = session.get(ComplianceEvaluation, record.compliance_evaluation_id)
                        if existing is None:
                            evaluated_at = record.evaluated_at
                            if evaluated_at.tzinfo is None:
                                evaluated_at = evaluated_at.replace(tzinfo=dt.UTC)

                            session.add(
                                ComplianceEvaluation(
                                    compliance_evaluation_id=record.compliance_evaluation_id,
                                    case_id=record.case_id,
                                    schema_version=record.schema_version,
                                    evaluated_at=evaluated_at,
                                    rule_results=record.rule_results,
                                    blockers=record.blockers,
                                    warnings=record.warnings,
                                    provenance=record.provenance,
                                    evidence_payload=record.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(record.compliance_evaluation_id)

                logger.info(
                    "compliance_activity.persisted workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    adapter_result.source_kind,
                    source_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )
                logger.info(
                    "activity.ok name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s source_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    source_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(ComplianceEvaluation)
                .filter(ComplianceEvaluation.compliance_evaluation_id.in_(fixture_ids))
                .all()
            )
            existing_ids = [row.compliance_evaluation_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    "compliance_evaluations insert raced but rows not found for compliance_evaluation_ids=%s"
                    % ",".join(fixture_ids)
                )

            logger.info(
                "compliance_activity.persisted workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                adapter_result.source_kind,
                source_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s source_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                source_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_incentive_assessment(
    request: PersistIncentiveAssessmentRequest | dict,
) -> list[str]:
    """Persist incentive assessment fixtures for a case idempotently."""

    req = PersistIncentiveAssessmentRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    fixtures, fixture_case_id = select_incentive_fixtures(req.case_id)
    logger.info(
        "activity.lookup name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        fixture_case_id,
        1 if fixture_case_id != req.case_id else 0,
    )
    if not fixtures:
        raise LookupError(
            "no incentive fixtures found for case_id=%s fixture_case_id=%s"
            % (req.case_id, fixture_case_id)
        )

    SessionLocal = get_sessionmaker()
    fixture_ids = [fixture.incentive_assessment_id for fixture in fixtures]
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for fixture in fixtures:
                        existing = session.get(IncentiveAssessment, fixture.incentive_assessment_id)
                        if existing is None:
                            assessed_at = fixture.assessed_at
                            if assessed_at.tzinfo is None:
                                assessed_at = assessed_at.replace(tzinfo=dt.UTC)

                            session.add(
                                IncentiveAssessment(
                                    incentive_assessment_id=fixture.incentive_assessment_id,
                                    case_id=fixture.case_id,
                                    schema_version=fixture.schema_version,
                                    assessed_at=assessed_at,
                                    candidate_programs=[
                                        program.model_dump(mode="json")
                                        for program in fixture.candidate_programs
                                    ],
                                    eligibility_status=fixture.eligibility_status,
                                    stacking_conflicts=fixture.stacking_conflicts,
                                    deadlines=[
                                        deadline.model_dump(mode="json")
                                        for deadline in fixture.deadlines
                                    ]
                                    if fixture.deadlines
                                    else None,
                                    source_ids=fixture.source_ids,
                                    advisory_value_range=fixture.advisory_value_range,
                                    authoritative_value_state=fixture.authoritative_value_state,
                                    provenance=fixture.provenance,
                                    evidence_payload=fixture.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(fixture.incentive_assessment_id)

                logger.info(
                    "incentives_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )
                logger.info(
                    "activity.ok name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(IncentiveAssessment)
                .filter(IncentiveAssessment.incentive_assessment_id.in_(fixture_ids))
                .all()
            )
            existing_ids = [row.incentive_assessment_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    "incentive_assessments insert raced but rows not found for incentive_assessment_ids=%s"
                    % ",".join(fixture_ids)
                )

            logger.info(
                "incentives_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_external_status_event(
    request: ExternalStatusNormalizationRequest | dict,
) -> ExternalStatusNormalizationResult:
    """Normalize and persist an ExternalStatusEvent with fail-closed behavior."""

    req = ExternalStatusNormalizationRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "external_status_event.persist.start workflow_id=%s run_id=%s case_id=%s event_id=%s submission_attempt_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.event_id,
        req.submission_attempt_id,
    )

    mapping_version: str | None = None
    adapter_result = get_runtime_adapters().load_status_mapping(req.case_id)
    selection = adapter_result.value
    mapping_version = selection.mapping_version
    mapping = selection.mappings.get(req.raw_status)
    if mapping is None:
        logger.error(
            "external_status_event.persist.error workflow_id=%s run_id=%s case_id=%s raw_status=%s source_kind=%s mapping_version=%s error=UNKNOWN_RAW_STATUS",
            workflow_id,
            run_id,
            req.case_id,
            req.raw_status,
            adapter_result.source_kind,
            selection.mapping_version,
        )
        raise ValueError("UNKNOWN_RAW_STATUS")

    normalized_status = ExternalStatusClass(mapping.normalized_status)
    confidence = ExternalStatusConfidence(mapping.confidence)
    auto_advance_eligible = bool(mapping.auto_advance)
    evidence_ids = sorted({*req.evidence_ids, *mapping.required_evidence})

    received_at = req.received_at or dt.datetime.now(dt.UTC)
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()

    def _row_to_result(row: ExternalStatusEvent) -> ExternalStatusNormalizationResult:
        return ExternalStatusNormalizationResult(
            event_id=row.event_id,
            case_id=row.case_id,
            submission_attempt_id=row.submission_attempt_id,
            raw_status=row.raw_status,
            normalized_status=ExternalStatusClass(row.normalized_status),
            confidence=ExternalStatusConfidence(row.confidence),
            auto_advance_eligible=row.auto_advance_eligible,
            evidence_ids=row.evidence_ids or [],
            mapping_version=row.mapping_version,
            received_at=row.received_at,
        )

    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(ExternalStatusEvent, req.event_id)
                    if existing is not None:
                        result = _row_to_result(existing)
                        logger.info(
                            "external_status_event.persist.ok workflow_id=%s run_id=%s case_id=%s event_id=%s normalized_status=%s mapping_version=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.event_id,
                            result.normalized_status,
                            result.mapping_version,
                        )
                        return result

                    case = session.get(PermitCase, req.case_id, with_for_update=True)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")

                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(
                            "submission_attempt not found for submission_attempt_id=%s"
                            % req.submission_attempt_id
                        )
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            "submission_attempt_case_mismatch attempt_id=%s case_id=%s"
                            % (req.submission_attempt_id, req.case_id)
                        )

                    event = ExternalStatusEvent(
                        event_id=req.event_id,
                        case_id=req.case_id,
                        submission_attempt_id=req.submission_attempt_id,
                        raw_status=req.raw_status,
                        normalized_status=normalized_status.value,
                        confidence=confidence.value,
                        auto_advance_eligible=auto_advance_eligible,
                        evidence_ids=evidence_ids,
                        mapping_version=selection.mapping_version,
                        received_at=received_at,
                    )
                    session.add(event)

                result = _row_to_result(event)
                logger.info(
                    "external_status_event.persist.ok workflow_id=%s run_id=%s case_id=%s event_id=%s normalized_status=%s mapping_version=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.event_id,
                    result.normalized_status,
                    result.mapping_version,
                )
                return result
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(ExternalStatusEvent, req.event_id)
            if existing is None:
                raise RuntimeError(
                    f"external_status_events insert raced but row not found for event_id={req.event_id}"
                )
            result = _row_to_result(existing)
            logger.info(
                "external_status_event.persist.ok workflow_id=%s run_id=%s case_id=%s event_id=%s normalized_status=%s mapping_version=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.event_id,
                result.normalized_status,
                result.mapping_version,
            )
            return result
    except Exception as exc:
        logger.exception(
            "external_status_event.persist.error workflow_id=%s run_id=%s case_id=%s event_id=%s mapping_version=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.event_id,
            mapping_version or "unknown",
            type(exc).__name__,
        )
        raise



def _safe_temporal_ids() -> tuple[str | None, str | None]:
    """Best-effort activity correlation identifiers.

    This activity is sometimes called directly in DB-level integration tests where
    Temporal activity context is unavailable.
    """

    try:
        info = activity.info()
        return info.workflow_id, info.workflow_run_id
    except Exception:
        return None, None


_EVENT_CASE_STATE_CHANGED = "CASE_STATE_CHANGED"
_EVENT_APPROVAL_GATE_DENIED = "APPROVAL_GATE_DENIED"
_EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"
_EVENT_OVERRIDE_DENIED = "OVERRIDE_DENIED"
_EVENT_INTAKE_PROJECT_DENIED = "INTAKE_PROJECT_REQUIRED_DENIED"
_EVENT_JURISDICTION_REQUIRED_DENIED = "JURISDICTION_REQUIRED_DENIED"
_EVENT_REQUIREMENTS_REQUIRED_DENIED = "REQUIREMENTS_REQUIRED_DENIED"
_EVENT_REQUIREMENTS_FRESHNESS_DENIED = "REQUIREMENTS_FRESHNESS_DENIED"
_EVENT_COMPLIANCE_REQUIRED_DENIED = "COMPLIANCE_REQUIRED_DENIED"
_EVENT_COMPLIANCE_FRESHNESS_DENIED = "COMPLIANCE_FRESHNESS_DENIED"
_EVENT_INCENTIVES_REQUIRED_DENIED = "INCENTIVES_REQUIRED_DENIED"
_EVENT_INCENTIVES_FRESHNESS_DENIED = "INCENTIVES_FRESHNESS_DENIED"
_EVENT_MANUAL_SUBMISSION_REQUIRED_DENIED = "MANUAL_SUBMISSION_REQUIRED_DENIED"
_EVENT_PROOF_BUNDLE_REQUIRED_DENIED = "PROOF_BUNDLE_REQUIRED_DENIED"
_GUARD_ASSERTION_REVIEW_GATE = "INV-SPS-STATE-002"
_GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"
_GUARD_ASSERTION_OVERRIDE = "INV-SPS-EMERG-001"
_GUARD_ASSERTION_REQUIREMENTS_FRESHNESS = "INV-SPS-RULE-001"
_GUARD_ASSERTION_COMPLIANCE_FRESHNESS = "INV-SPS-COMP-001"
_GUARD_ASSERTION_INCENTIVES_FRESHNESS = "INV-SPS-INC-001"
_ALLOWED_REVIEW_OUTCOMES = {"ACCEPT", "ACCEPT_WITH_DISSENT"}


def _deny(
    *,
    denied_at: dt.datetime,
    event_type: str,
    denial_reason: str,
    guard_assertion_id: str | None = None,
    normalized_business_invariants: list[str] | None = None,
) -> DeniedStateTransitionResult:
    return DeniedStateTransitionResult(
        event_type=event_type,
        denied_at=denied_at,
        denial_reason=denial_reason,
        guard_assertion_id=guard_assertion_id,
        normalized_business_invariants=normalized_business_invariants,
    )


def _validate_override(
    *,
    session,
    req: StateTransitionRequest,
    requested_at: dt.datetime,
    workflow_id: str | None,
    run_id: str | None,
) -> DeniedStateTransitionResult | None:
    if req.override_id is None:
        return None

    transition = f"{req.from_state.value}->{req.to_state.value}"

    def _deny_override(reason: str) -> DeniedStateTransitionResult:
        invariants = get_normalized_business_invariants(_GUARD_ASSERTION_OVERRIDE)
        logger.warning(
            "workflow.override_denied workflow_id=%s run_id=%s case_id=%s transition=%s override_id=%s denial_reason=%s guard_assertion_id=%s normalized_business_invariants=%s",
            workflow_id,
            run_id,
            req.case_id,
            transition,
            req.override_id,
            reason,
            _GUARD_ASSERTION_OVERRIDE,
            invariants,
        )
        return _deny(
            denied_at=requested_at,
            event_type=_EVENT_OVERRIDE_DENIED,
            denial_reason=reason,
            guard_assertion_id=_GUARD_ASSERTION_OVERRIDE,
            normalized_business_invariants=invariants,
        )

    override = session.get(OverrideArtifact, req.override_id)
    if override is None or override.case_id != req.case_id:
        return _deny_override("missing")

    override_expires_at = override.expires_at
    if override_expires_at.tzinfo is None:
        override_expires_at = override_expires_at.replace(tzinfo=dt.UTC)

    if override_expires_at <= requested_at:
        return _deny_override("expired")

    affected_surfaces = list(override.affected_surfaces or [])
    if transition not in affected_surfaces:
        return _deny_override("out_of_scope")

    return None


@activity.defn
def apply_state_transition(request: StateTransitionRequest | dict) -> StateTransitionResult:
    """Authoritative Postgres-backed transition guard + state mutation.

    - Fail-closed: unknown transitions and missing preconditions return a structured denial.
    - Durable audit: both applied and denied attempts are persisted to case_transition_ledger.
    - Idempotent: request.request_id is treated as the ledger primary key.
    """

    req = StateTransitionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    requested_at = req.requested_at
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=dt.UTC)

    logger.info(
        "activity.start name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s",
        workflow_id,
        run_id,
        req.request_id,
        req.case_id,
        req.from_state,
        req.to_state,
    )

    SessionLocal = get_sessionmaker()

    # First attempt in a single transaction; on a rare INSERT race we re-load.
    try:
        with SessionLocal() as session:
            try:
                idempotent = False
                persisted_event_type: str | None = None

                with session.begin():
                    existing = session.get(CaseTransitionLedger, req.request_id)
                    if existing is not None:
                        idempotent = True
                        persisted_event_type = existing.event_type
                        if existing.payload is None:
                            result = _deny(
                                denied_at=requested_at,
                                event_type=existing.event_type,
                                denial_reason="LEDGER_PAYLOAD_MISSING",
                            )
                        else:
                            result = parse_state_transition_result(existing.payload)
                    else:
                        case = session.get(PermitCase, req.case_id, with_for_update=True)
                        if case is None:
                            # With the current schema, we cannot write an audit row without
                            # an existing PermitCase due to FK constraints.
                            raise LookupError(f"permit_cases row not found for case_id={req.case_id}")

                        if case.case_state != req.from_state.value:
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="FROM_STATE_MISMATCH",
                            )
                        elif req.to_state == CaseState.EMERGENCY_HOLD:
                            result = AppliedStateTransitionResult(
                                event_type=_EVENT_CASE_STATE_CHANGED,
                                applied_at=requested_at,
                            )
                            case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.EMERGENCY_HOLD
                            and req.to_state == CaseState.SUBMITTED
                        ):
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="FORBIDDEN_TRANSITION",
                            )
                        elif (
                            req.from_state == CaseState.EMERGENCY_HOLD
                            and req.to_state != CaseState.EMERGENCY_HOLD
                        ):
                            result = AppliedStateTransitionResult(
                                event_type=_EVENT_CASE_STATE_CHANGED,
                                applied_at=requested_at,
                            )
                            case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.REVIEW_PENDING
                            and req.to_state == CaseState.APPROVED_FOR_SUBMISSION
                        ):
                            def _apply_review_gate() -> StateTransitionResult:
                                # Canonical protected transition: requires a valid ReviewDecision.
                                invariants = get_normalized_business_invariants(_GUARD_ASSERTION_REVIEW_GATE)

                                review_id = req.required_review_id
                                review: ReviewDecision | None = (
                                    session.get(ReviewDecision, review_id) if review_id else None
                                )

                                if (
                                    review_id is None
                                    or review is None
                                    or review.case_id != req.case_id
                                    or review.decision_outcome not in _ALLOWED_REVIEW_OUTCOMES
                                ):
                                    return _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_APPROVAL_GATE_DENIED,
                                        denial_reason="REVIEW_DECISION_REQUIRED",
                                        guard_assertion_id=_GUARD_ASSERTION_REVIEW_GATE,
                                        normalized_business_invariants=invariants,
                                    )

                                case.case_state = req.to_state.value
                                return AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )

                            if req.override_id is not None:
                                # Override validation is evaluated before contradiction checks so overrides can
                                # explicitly bypass contradiction blocks when authorized.
                                override_denial = _validate_override(
                                    session=session,
                                    req=req,
                                    requested_at=requested_at,
                                    workflow_id=workflow_id,
                                    run_id=run_id,
                                )

                                if override_denial is not None:
                                    result = override_denial
                                else:
                                    result = _apply_review_gate()
                            else:
                                # Guard: blocking open contradictions must be resolved before advancement (CTL-14A).
                                blocking_contradiction = (
                                    session.query(ContradictionArtifact)
                                    .filter(
                                        ContradictionArtifact.case_id == req.case_id,
                                        ContradictionArtifact.blocking_effect.is_(True),
                                        ContradictionArtifact.resolution_status == "OPEN",
                                    )
                                    .first()
                                )
                                if blocking_contradiction is not None:
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_CONTRADICTION_ADVANCE_DENIED,
                                        denial_reason="BLOCKING_CONTRADICTION_UNRESOLVED",
                                        guard_assertion_id=_GUARD_ASSERTION_CONTRADICTION,
                                        normalized_business_invariants=get_normalized_business_invariants(
                                            _GUARD_ASSERTION_CONTRADICTION
                                        ),
                                    )
                                else:
                                    result = _apply_review_gate()
                        elif (
                            req.from_state == CaseState.INTAKE_PENDING
                            and req.to_state == CaseState.INTAKE_COMPLETE
                        ):
                            project = (
                                session.query(Project)
                                .filter(Project.case_id == req.case_id)
                                .one_or_none()
                            )
                            if project is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_INTAKE_PROJECT_DENIED,
                                    denial_reason="PROJECT_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.INTAKE_COMPLETE
                            and req.to_state == CaseState.JURISDICTION_COMPLETE
                        ):
                            resolution = (
                                session.query(JurisdictionResolution)
                                .filter(JurisdictionResolution.case_id == req.case_id)
                                .first()
                            )
                            if resolution is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_JURISDICTION_REQUIRED_DENIED,
                                    denial_reason="JURISDICTION_RESOLUTION_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.JURISDICTION_COMPLETE
                            and req.to_state == CaseState.RESEARCH_COMPLETE
                        ):
                            requirement_set = (
                                session.query(RequirementSet)
                                .filter(RequirementSet.case_id == req.case_id)
                                .first()
                            )
                            invariants = get_normalized_business_invariants(
                                _GUARD_ASSERTION_REQUIREMENTS_FRESHNESS
                            )
                            if requirement_set is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_REQUIREMENTS_REQUIRED_DENIED,
                                    denial_reason="REQUIREMENT_SET_REQUIRED",
                                    guard_assertion_id=_GUARD_ASSERTION_REQUIREMENTS_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            elif requirement_set.freshness_state != "FRESH":
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_REQUIREMENTS_FRESHNESS_DENIED,
                                    denial_reason="REQUIREMENT_SET_STALE",
                                    guard_assertion_id=_GUARD_ASSERTION_REQUIREMENTS_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.RESEARCH_COMPLETE
                            and req.to_state == CaseState.COMPLIANCE_COMPLETE
                        ):
                            compliance_eval = (
                                session.query(ComplianceEvaluation)
                                .filter(ComplianceEvaluation.case_id == req.case_id)
                                .order_by(ComplianceEvaluation.evaluated_at.desc())
                                .first()
                            )
                            invariants = get_normalized_business_invariants(
                                _GUARD_ASSERTION_COMPLIANCE_FRESHNESS
                            )
                            if compliance_eval is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_COMPLIANCE_REQUIRED_DENIED,
                                    denial_reason="COMPLIANCE_EVALUATION_REQUIRED",
                                    guard_assertion_id=_GUARD_ASSERTION_COMPLIANCE_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            else:
                                evaluated_at = compliance_eval.evaluated_at
                                if evaluated_at.tzinfo is None:
                                    evaluated_at = evaluated_at.replace(tzinfo=dt.UTC)
                                freshness_deadline = requested_at - dt.timedelta(days=30)
                                if evaluated_at < freshness_deadline:
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_COMPLIANCE_FRESHNESS_DENIED,
                                        denial_reason="COMPLIANCE_EVALUATION_STALE",
                                        guard_assertion_id=_GUARD_ASSERTION_COMPLIANCE_FRESHNESS,
                                        normalized_business_invariants=invariants,
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.COMPLIANCE_COMPLETE
                            and req.to_state == CaseState.INCENTIVES_COMPLETE
                        ):
                            incentive_assessment = (
                                session.query(IncentiveAssessment)
                                .filter(IncentiveAssessment.case_id == req.case_id)
                                .order_by(IncentiveAssessment.assessed_at.desc())
                                .first()
                            )
                            invariants = get_normalized_business_invariants(
                                _GUARD_ASSERTION_INCENTIVES_FRESHNESS
                            )
                            if incentive_assessment is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_INCENTIVES_REQUIRED_DENIED,
                                    denial_reason="INCENTIVE_ASSESSMENT_REQUIRED",
                                    guard_assertion_id=_GUARD_ASSERTION_INCENTIVES_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            else:
                                assessed_at = incentive_assessment.assessed_at
                                if assessed_at.tzinfo is None:
                                    assessed_at = assessed_at.replace(tzinfo=dt.UTC)
                                freshness_deadline = requested_at - dt.timedelta(days=3)
                                if assessed_at < freshness_deadline:
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_INCENTIVES_FRESHNESS_DENIED,
                                        denial_reason="INCENTIVE_ASSESSMENT_STALE",
                                        guard_assertion_id=_GUARD_ASSERTION_INCENTIVES_FRESHNESS,
                                        normalized_business_invariants=invariants,
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.INCENTIVES_COMPLETE
                            and req.to_state == CaseState.DOCUMENT_COMPLETE
                        ):
                            # Guard: submission package must exist
                            package = (
                                session.query(SubmissionPackage)
                                .filter(SubmissionPackage.case_id == req.case_id)
                                .first()
                            )
                            if package is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type="DOCUMENT_PACKAGE_REQUIRED_DENIED",
                                    denial_reason="SUBMISSION_PACKAGE_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.DOCUMENT_COMPLETE
                            and req.to_state == CaseState.MANUAL_SUBMISSION_REQUIRED
                        ):
                            fallback = (
                                session.query(ManualFallbackPackage)
                                .filter(ManualFallbackPackage.case_id == req.case_id)
                                .order_by(ManualFallbackPackage.created_at.desc())
                                .first()
                            )
                            if fallback is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_MANUAL_SUBMISSION_REQUIRED_DENIED,
                                    denial_reason="MANUAL_FALLBACK_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.DOCUMENT_COMPLETE
                            and req.to_state == CaseState.SUBMITTED
                        ):
                            fallback = (
                                session.query(ManualFallbackPackage)
                                .filter(ManualFallbackPackage.case_id == req.case_id)
                                .order_by(ManualFallbackPackage.created_at.desc())
                                .first()
                            )
                            if fallback is not None:
                                if (
                                    fallback.proof_bundle_state != "CONFIRMED"
                                    or fallback.proof_bundle_artifact_id is None
                                ):
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_PROOF_BUNDLE_REQUIRED_DENIED,
                                        denial_reason="PROOF_BUNDLE_REQUIRED",
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.SUBMITTED
                            and req.to_state == CaseState.COMMENT_REVIEW_PENDING
                        ):
                            # Post-submission: external status COMMENT_ISSUED triggers this transition
                            result = AppliedStateTransitionResult(
                                event_type=_EVENT_CASE_STATE_CHANGED,
                                applied_at=requested_at,
                            )
                            case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.COMMENT_REVIEW_PENDING
                            and req.to_state == CaseState.CORRECTION_PENDING
                        ):
                            # Move from comment review to correction work
                            result = AppliedStateTransitionResult(
                                event_type=_EVENT_CASE_STATE_CHANGED,
                                applied_at=requested_at,
                            )
                            case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.CORRECTION_PENDING
                            and req.to_state == CaseState.RESUBMISSION_PENDING
                        ):
                            # Corrections complete, ready for resubmission
                            result = AppliedStateTransitionResult(
                                event_type=_EVENT_CASE_STATE_CHANGED,
                                applied_at=requested_at,
                            )
                            case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.RESUBMISSION_PENDING
                            and req.to_state == CaseState.DOCUMENT_COMPLETE
                        ):
                            # Resubmission path: back to DOCUMENT_COMPLETE to regenerate package
                            result = AppliedStateTransitionResult(
                                event_type=_EVENT_CASE_STATE_CHANGED,
                                applied_at=requested_at,
                            )
                            case.case_state = req.to_state.value
                        else:
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="UNKNOWN_TRANSITION",
                            )

                        emit_audit_event(
                            session,
                            action=(
                                "state_transition.applied"
                                if result.result == "applied"
                                else "state_transition.denied"
                            ),
                            actor_type=req.actor_type.value,
                            actor_id=req.actor_id,
                            correlation_id=req.correlation_id,
                            request_id=req.request_id,
                            payload={
                                "case_id": req.case_id,
                                "from_state": req.from_state.value,
                                "to_state": req.to_state.value,
                                "result": result.result,
                                "event_type": result.event_type,
                                "denial_reason": getattr(result, "denial_reason", None),
                                "guard_assertion_id": getattr(result, "guard_assertion_id", None),
                            },
                            occurred_at=requested_at,
                        )

                        session.add(
                            CaseTransitionLedger(
                                transition_id=req.request_id,
                                case_id=req.case_id,
                                event_type=result.event_type,
                                from_state=req.from_state.value,
                                to_state=req.to_state.value,
                                actor_type=req.actor_type.value,
                                actor_id=req.actor_id,
                                correlation_id=req.correlation_id,
                                occurred_at=requested_at,
                                payload=result.model_dump(mode="json"),
                            )
                        )
                        persisted_event_type = result.event_type

                failpoint_key = f"apply_state_transition.after_commit/{req.request_id}"
                try:
                    fail_once(failpoint_key)
                except FailpointFired:
                    logger.error(
                        "activity.failpoint name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s correlation_id=%s failpoint_key=%s",
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        req.correlation_id,
                        failpoint_key,
                    )
                    raise

                if idempotent:
                    logger.info(
                        "activity.ok name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s event_type=%s result=%s idempotent=1",
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        persisted_event_type,
                        result.result,
                    )
                else:
                    log_event = "activity.ok" if result.result == "applied" else "activity.denied"
                    logger.info(
                        "%s name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s event_type=%s result=%s idempotent=0",
                        log_event,
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        req.from_state,
                        req.to_state,
                        result.event_type,
                        result.result,
                    )

                return result
            except IntegrityError:
                # If we raced another attempt with the same request_id, the primary key
                # ensures we can safely re-load and return the persisted outcome.
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(CaseTransitionLedger, req.request_id)
            if existing is None:
                raise RuntimeError(f"ledger insert failed but row not found for request_id={req.request_id}")
            if existing.payload is None:
                result = _deny(
                    denied_at=requested_at,
                    event_type=existing.event_type,
                    denial_reason="LEDGER_PAYLOAD_MISSING",
                )
            else:
                result = parse_state_transition_result(existing.payload)

            logger.info(
                "activity.ok name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s event_type=%s result=%s idempotent=1",
                workflow_id,
                run_id,
                req.request_id,
                req.case_id,
                existing.event_type,
                result.result,
            )
            return result
    except Exception as exc:
        logger.exception(
            "activity.error name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s exc_type=%s",
            workflow_id,
            run_id,
            req.request_id,
            req.case_id,
            req.from_state,
            req.to_state,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_review_decision(request: PersistReviewDecisionRequest | dict) -> str:
    """Persist a ReviewDecision row idempotently.

    Idempotency boundary: review_decisions.idempotency_key (unique).

    Returns:
        The persisted decision_id.
    """

    req = PersistReviewDecisionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    decision_at = req.decision_at
    if decision_at.tzinfo is None:
        decision_at = decision_at.replace(tzinfo=dt.UTC)

    logger.info(
        "activity.start name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotency_key=%s outcome=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.decision_id,
        req.idempotency_key,
        req.decision_outcome,
    )

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                idempotent = False
                persisted_decision_id: str | None = None

                with session.begin():
                    existing = (
                        session.query(ReviewDecision)
                        .filter(ReviewDecision.idempotency_key == req.idempotency_key)
                        .one_or_none()
                    )
                    if existing is not None:
                        idempotent = True
                        persisted_decision_id = existing.decision_id
                    else:
                        session.add(
                            ReviewDecision(
                                decision_id=req.decision_id,
                                schema_version=req.schema_version,
                                case_id=req.case_id,
                                object_type=req.object_type,
                                object_id=req.object_id,
                                decision_outcome=req.decision_outcome.value,
                                reviewer_id=req.reviewer_id,
                                reviewer_independence_status=req.reviewer_independence_status.value,
                                evidence_ids=req.evidence_ids,
                                contradiction_resolution=req.contradiction_resolution,
                                dissent_flag=req.dissent_flag,
                                notes=req.notes,
                                decision_at=decision_at,
                                idempotency_key=req.idempotency_key,
                            )
                        )
                        persisted_decision_id = req.decision_id

                assert persisted_decision_id is not None

                failpoint_key = f"persist_review_decision.after_commit/{req.idempotency_key}"
                try:
                    fail_once(failpoint_key)
                except FailpointFired:
                    logger.error(
                        "activity.failpoint name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotency_key=%s failpoint_key=%s",
                        workflow_id,
                        run_id,
                        req.case_id,
                        persisted_decision_id,
                        req.idempotency_key,
                        failpoint_key,
                    )
                    raise

                logger.info(
                    "activity.ok name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    persisted_decision_id,
                    1 if idempotent else 0,
                )
                return persisted_decision_id
            except IntegrityError:
                session.rollback()
                raced = (
                    session.query(ReviewDecision)
                    .filter(ReviewDecision.idempotency_key == req.idempotency_key)
                    .one_or_none()
                )
                if raced is None:
                    raise RuntimeError(
                        "review_decisions insert raced but row not found for idempotency_key="
                        f"{req.idempotency_key}"
                    )

                logger.info(
                    "activity.ok name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotent=1",
                    workflow_id,
                    run_id,
                    req.case_id,
                    raced.decision_id,
                )
                return raced.decision_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.decision_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_submission_package(request: PersistSubmissionPackageRequest | dict) -> str:
    """
    Persist submission package + document artifacts idempotently.
    
    Generates documents from adapter-backed document specs, registers them in evidence registry,
    stores SubmissionPackage row + DocumentArtifact rows, and updates 
    permit_cases.current_package_id in a single transaction.
    
    Returns the persisted package_id.
    """
    from sps.config import get_settings
    from sps.db.models import EvidenceArtifact
    from sps.documents.contracts import ManifestDocumentReference, SubmissionManifestPayload
    from sps.documents.generator import generate_submission_package
    from sps.documents.registry import EvidenceRegistry
    from sps.evidence.ids import new_evidence_id
    from sps.documents.contracts import DocumentType
    from sps.evidence.models import ArtifactClass, RetentionClass
    from sps.storage.s3 import S3Storage
    
    req = PersistSubmissionPackageRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()
    
    logger.info(
        "activity.start name=persist_submission_package workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )
    
    adapter_result = get_runtime_adapters().load_documents(req.case_id)
    compilation = adapter_result.value
    logger.info(
        "activity.lookup name=persist_submission_package workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        adapter_result.source_kind,
        adapter_result.source_key,
        1 if adapter_result.source_key != req.case_id else 0,
    )

    if not compilation.documents:
        raise LookupError(
            "no document adapter data found for case_id=%s source_case_id=%s"
            % (req.case_id, adapter_result.source_key)
        )

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        existing_packages = (
            session.query(SubmissionPackage)
            .filter(SubmissionPackage.case_id == req.case_id)
            .order_by(SubmissionPackage.created_at.desc())
            .all()
        )
        for existing in existing_packages:
            provenance = existing.provenance or {}
            if provenance.get("request_id") == req.request_id:
                logger.info(
                    "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s idempotent=1",
                    workflow_id,
                    run_id,
                    req.case_id,
                    existing.package_id,
                )
                return existing.package_id

    # Generate submission package with all documents
    package_payload = generate_submission_package(compilation, runtime_case_id=req.case_id)
    package_id = package_payload.package_id
    
    # Initialize evidence registry
    settings = get_settings()
    storage = S3Storage(settings=settings)
    registry = EvidenceRegistry(storage=storage, settings=settings)

    registered_documents: list[tuple[object, object]] = []
    for doc_payload in package_payload.document_artifacts:
        doc_reg = registry.register_document(
            content=doc_payload.content_bytes,
            case_id=req.case_id,
            document_type=doc_payload.document_type.value,
            provenance={
                "document_id": doc_payload.document_id,
                "template_name": doc_payload.template_name,
            },
        )
        registered_documents.append((doc_payload, doc_reg))

    actual_manifest = SubmissionManifestPayload(
        manifest_id=package_payload.manifest.manifest_id,
        case_id=req.case_id,
        package_version=package_payload.package_version,
        generated_at=package_payload.manifest.generated_at,
        document_references=[
            ManifestDocumentReference(
                document_id=doc_payload.document_id,
                document_type=DocumentType(doc_payload.document_type),
                artifact_id=doc_reg.artifact_id,
                sha256_digest=doc_reg.sha256_digest,
            )
            for doc_payload, doc_reg in registered_documents
        ],
        required_attachments=package_payload.manifest.required_attachments,
        target_portal_family=package_payload.manifest.target_portal_family,
        provenance=package_payload.manifest.provenance,
    )

    manifest_json = actual_manifest.model_dump_json(exclude_none=True, indent=None)
    manifest_bytes = manifest_json.encode("utf-8")
    manifest_reg = registry.register_manifest(
        content=manifest_bytes,
        case_id=req.case_id,
        provenance={"package_id": package_id, "request_id": req.request_id},
    )

    logger.info(
        "package_activity.manifest_registered case_id=%s manifest_id=%s artifact_id=%s digest=%s bytes=%d",
        req.case_id,
        actual_manifest.manifest_id,
        manifest_reg.artifact_id,
        manifest_reg.sha256_digest,
        manifest_reg.content_bytes,
    )
    
    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    # Check if package already exists (idempotency)
                    existing = session.get(SubmissionPackage, package_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            package_id,
                        )
                        return package_id
                    
                    # Create manifest evidence artifact
                    session.add(
                        EvidenceArtifact(
                            artifact_id=manifest_reg.artifact_id,
                            artifact_class=ArtifactClass.MANIFEST.value,
                            producing_service="permit_case_workflow",
                            linked_case_id=req.case_id,
                            linked_object_id=package_id,
                            authoritativeness="AUTHORITATIVE",
                            retention_class=RetentionClass.CASE_CORE_7Y.value,
                            checksum=manifest_reg.sha256_digest,
                            storage_uri=manifest_reg.storage_uri,
                            content_bytes=manifest_reg.content_bytes,
                            content_type="application/json",
                            provenance={"request_id": req.request_id, "manifest_id": package_payload.manifest.manifest_id},
                            created_at=dt.datetime.now(dt.UTC),
                            legal_hold_flag=False,
                        )
                    )
                    session.flush()
                    
                    # Create submission package
                    session.add(
                        SubmissionPackage(
                            package_id=package_id,
                            case_id=req.case_id,
                            package_version=package_payload.package_version,
                            manifest_artifact_id=manifest_reg.artifact_id,
                            manifest_sha256_digest=manifest_reg.sha256_digest,
                            provenance={
                                "request_id": req.request_id,
                                "document_set_id": compilation.document_set_id,
                                "source_kind": adapter_result.source_kind,
                            },
                        )
                    )
                    
                    # Flush to ensure package exists before document artifacts
                    session.flush()
                    
                    # Persist document artifacts after their evidence IDs are fixed.
                    doc_count = 0
                    for doc_payload, doc_reg in registered_documents:
                        # Evidence artifact for document
                        session.add(
                            EvidenceArtifact(
                                artifact_id=doc_reg.artifact_id,
                                artifact_class=ArtifactClass.DOCUMENT.value,
                                producing_service="permit_case_workflow",
                                linked_case_id=req.case_id,
                                linked_object_id=doc_payload.document_id,
                                authoritativeness="AUTHORITATIVE",
                                retention_class=RetentionClass.CASE_CORE_7Y.value,
                                checksum=doc_reg.sha256_digest,
                                storage_uri=doc_reg.storage_uri,
                                content_bytes=doc_reg.content_bytes,
                                content_type="text/plain",
                                provenance={"document_id": doc_payload.document_id},
                                created_at=dt.datetime.now(dt.UTC),
                                legal_hold_flag=False,
                            )
                        )
                        session.flush()

                        # Document artifact row
                        session.add(
                            DocumentArtifact(
                                document_artifact_id=new_evidence_id(),
                                package_id=package_id,
                                document_id=doc_payload.document_id,
                                document_type=doc_payload.document_type.value,
                                template_name=doc_payload.template_name,
                                evidence_artifact_id=doc_reg.artifact_id,
                                sha256_digest=doc_reg.sha256_digest,
                                provenance={"template_name": doc_payload.template_name},
                            )
                        )
                        doc_count += 1
                    
                    # Update permit_cases.current_package_id
                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise RuntimeError(f"permit_case not found: {req.case_id}")
                    case.current_package_id = package_id
                    if case.case_state == CaseState.INCENTIVES_COMPLETE.value:
                        case.case_state = CaseState.DOCUMENT_COMPLETE.value
                    
                    logger.info(
                        "package_activity.persisted workflow_id=%s run_id=%s case_id=%s package_id=%s manifest_id=%s doc_count=%s",
                        workflow_id,
                        run_id,
                        req.case_id,
                        package_id,
                        manifest_reg.artifact_id,
                        doc_count,
                    )
                
                logger.info(
                    "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    package_id,
                )
                return package_id
                
            except IntegrityError as e:
                session.rollback()
                existing = (
                    session.query(SubmissionPackage)
                    .filter(SubmissionPackage.case_id == req.case_id)
                    .order_by(SubmissionPackage.created_at.desc())
                    .all()
                )
                raced = next(
                    (
                        row
                        for row in existing
                        if (row.provenance or {}).get("request_id") == req.request_id
                    ),
                    None,
                )
                if raced is None:
                    raise RuntimeError(
                        "submission_packages insert raced but row not found for "
                        f"case_id={req.case_id} request_id={req.request_id}"
                    ) from e
                
                logger.info(
                    "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s idempotent=1",
                    workflow_id,
                    run_id,
                    req.case_id,
                    raced.package_id,
                )
                return raced.package_id
                
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_submission_package workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def deterministic_submission_adapter(
    request: SubmissionAdapterRequest | dict,
) -> SubmissionAdapterResult:
    """Deterministic submission adapter activity with idempotent persistence."""

    import hashlib

    from sps.config import get_settings
    from sps.evidence.ids import evidence_object_key, new_evidence_id
    from sps.evidence.models import ArtifactClass, RetentionClass
    from sps.storage.s3 import S3Storage

    req = SubmissionAdapterRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "submission_attempt.start workflow_id=%s run_id=%s case_id=%s request_id=%s correlation_id=%s attempt_id=%s package_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
        req.correlation_id,
        req.submission_attempt_id,
        req.package_id,
    )

    SessionLocal = get_sessionmaker()

    def _load_existing_result(
        session,
        attempt: SubmissionAttempt,
    ) -> SubmissionAdapterResult:
        manual = (
            session.query(ManualFallbackPackage)
            .filter(ManualFallbackPackage.submission_attempt_id == attempt.submission_attempt_id)
            .one_or_none()
        )
        outcome_value = attempt.outcome or SubmissionAdapterOutcome.FAILED.value
        return SubmissionAdapterResult(
            submission_attempt_id=attempt.submission_attempt_id,
            status=attempt.status,
            outcome=SubmissionAdapterOutcome(outcome_value),
            external_tracking_id=attempt.external_tracking_id,
            receipt_artifact_id=attempt.receipt_artifact_id,
            submitted_at=attempt.submitted_at,
            manual_fallback_package_id=manual.manual_fallback_package_id if manual else None,
            portal_support_level=attempt.portal_support_level,
            failure_class=attempt.failure_class,
        )

    def _resolve_required_attachments(
        session,
        *,
        package: SubmissionPackage,
        attachment_sources: list[str],
    ) -> list[str]:
        attachments: list[str] = []
        sources = {source.upper() for source in attachment_sources}
        if "MANIFEST" in sources:
            attachments.append(package.manifest_artifact_id)
        if "DOCUMENTS" in sources:
            doc_rows = (
                session.query(DocumentArtifact)
                .filter(DocumentArtifact.package_id == package.package_id)
                .all()
            )
            attachments.extend([row.evidence_artifact_id for row in doc_rows])
        return sorted({item for item in attachments if item})

    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if existing is not None:
                        result = _load_existing_result(session, existing)
                        logger.info(
                            "submission_attempt.ok workflow_id=%s run_id=%s case_id=%s attempt_id=%s status=%s outcome=%s receipt_artifact_id=%s manual_fallback_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            existing.submission_attempt_id,
                            existing.status,
                            existing.outcome,
                            existing.receipt_artifact_id,
                            result.manual_fallback_package_id,
                        )
                        return result

                    case = session.get(PermitCase, req.case_id, with_for_update=True)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")
                    package = session.get(SubmissionPackage, req.package_id)
                    if package is None:
                        raise LookupError(f"submission_package not found for package_id={req.package_id}")

                    attempt = SubmissionAttempt(
                        submission_attempt_id=req.submission_attempt_id,
                        case_id=req.case_id,
                        package_id=req.package_id,
                        manifest_artifact_id=package.manifest_artifact_id,
                        target_portal_family=req.target_portal_family,
                        portal_support_level=case.portal_support_level,
                        request_id=req.request_id,
                        idempotency_key=req.idempotency_key,
                        attempt_number=req.attempt_number,
                        status="PENDING",
                        outcome=None,
                        external_tracking_id=None,
                        receipt_artifact_id=None,
                        submitted_at=None,
                        failure_class=None,
                        last_error=None,
                        last_error_context=None,
                    )
                    session.add(attempt)
                    session.flush()

                    support_level = case.portal_support_level or "UNKNOWN"
                    fallback_required = support_level in {
                        "UNSUPPORTED",
                        "PARTIALLY_SUPPORTED_READ_ONLY",
                    }

                    adapter_plan_result = get_runtime_adapters().load_submission_plan(
                        req.case_id,
                        target_portal_family=req.target_portal_family,
                    )
                    plan = adapter_plan_result.value
                    if plan is None:
                        logger.info(
                            "submission_attempt.plan_missing workflow_id=%s run_id=%s case_id=%s source_kind=%s source_case_id=%s",
                            workflow_id,
                            run_id,
                            req.case_id,
                            adapter_plan_result.source_kind,
                            adapter_plan_result.source_key,
                        )

                    if fallback_required:
                        manual_fallback_id = f"MFP-{req.submission_attempt_id}"
                        attachment_sources = (
                            plan.required_attachment_sources if plan else ["MANIFEST"]
                        )
                        required_attachments = _resolve_required_attachments(
                            session,
                            package=package,
                            attachment_sources=attachment_sources,
                        )
                        manual = ManualFallbackPackage(
                            manual_fallback_package_id=manual_fallback_id,
                            case_id=req.case_id,
                            package_id=package.package_id,
                            submission_attempt_id=attempt.submission_attempt_id,
                            package_version=package.package_version,
                            package_hash=package.manifest_sha256_digest,
                            reason=plan.reason if plan and plan.reason else "UNSUPPORTED_PORTAL_WORKFLOW",
                            portal_support_level=support_level,
                            channel_type=plan.channel_type if plan else "official_authority_email",
                            proof_bundle_state="PENDING_REVIEW",
                            required_attachments=required_attachments,
                            operator_instructions=plan.operator_instructions if plan else [],
                            required_proof_types=plan.required_proof_types if plan else [],
                            escalation_owner=plan.escalation_owner if plan else None,
                            proof_bundle_artifact_id=None,
                        )
                        session.add(manual)

                        attempt.status = "MANUAL_FALLBACK"
                        attempt.outcome = SubmissionAdapterOutcome.UNSUPPORTED_WORKFLOW.value

                        result = SubmissionAdapterResult(
                            submission_attempt_id=attempt.submission_attempt_id,
                            status=attempt.status,
                            outcome=SubmissionAdapterOutcome.UNSUPPORTED_WORKFLOW,
                            external_tracking_id=None,
                            receipt_artifact_id=None,
                            submitted_at=None,
                            manual_fallback_package_id=manual.manual_fallback_package_id,
                            portal_support_level=support_level,
                            failure_class=None,
                        )
                    else:
                        settings = get_settings()
                        storage = S3Storage(settings=settings)
                        storage.ensure_bucket(settings.s3_bucket_evidence)
                        artifact_id = new_evidence_id()
                        object_key = evidence_object_key(artifact_id)
                        external_tracking_id = f"{req.target_portal_family}-{req.submission_attempt_id}"
                        receipt_payload = (
                            f"receipt: case={req.case_id} attempt={req.submission_attempt_id} "
                            f"tracking={external_tracking_id}"
                        )
                        receipt_bytes = receipt_payload.encode("utf-8")
                        receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
                        put_result = storage.put_bytes(
                            bucket=settings.s3_bucket_evidence,
                            key=object_key,
                            content=receipt_bytes,
                            expected_sha256_hex=receipt_sha256,
                            content_type="text/plain",
                        )
                        submitted_at = dt.datetime.now(dt.UTC)
                        session.add(
                            EvidenceArtifact(
                                artifact_id=artifact_id,
                                artifact_class=ArtifactClass.RECEIPT.value,
                                producing_service="permit_case_workflow",
                                linked_case_id=req.case_id,
                                linked_object_id=attempt.submission_attempt_id,
                                authoritativeness="AUTHORITATIVE",
                                retention_class=RetentionClass.CASE_CORE_7Y.value,
                                checksum=put_result.sha256_hex,
                                storage_uri=f"s3://{put_result.bucket}/{put_result.key}",
                                content_bytes=put_result.bytes,
                                content_type="text/plain",
                                provenance={
                                    "request_id": req.request_id,
                                    "manifest_id": req.manifest_id,
                                    "target_portal_family": req.target_portal_family,
                                },
                                created_at=submitted_at,
                                legal_hold_flag=False,
                            )
                        )

                        attempt.status = "SUBMITTED"
                        attempt.outcome = SubmissionAdapterOutcome.SUCCESS.value
                        attempt.external_tracking_id = external_tracking_id
                        attempt.receipt_artifact_id = artifact_id
                        attempt.submitted_at = submitted_at

                        result = SubmissionAdapterResult(
                            submission_attempt_id=attempt.submission_attempt_id,
                            status=attempt.status,
                            outcome=SubmissionAdapterOutcome.SUCCESS,
                            external_tracking_id=external_tracking_id,
                            receipt_artifact_id=artifact_id,
                            submitted_at=submitted_at,
                            manual_fallback_package_id=None,
                            portal_support_level=support_level,
                            failure_class=None,
                        )

                logger.info(
                    "submission_attempt.ok workflow_id=%s run_id=%s case_id=%s attempt_id=%s status=%s outcome=%s receipt_artifact_id=%s manual_fallback_id=%s idempotent=0",
                    workflow_id,
                    run_id,
                    req.case_id,
                    result.submission_attempt_id,
                    result.status,
                    result.outcome,
                    result.receipt_artifact_id,
                    result.manual_fallback_package_id,
                )
                return result
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = (
                session.query(SubmissionAttempt)
                .filter(
                    (SubmissionAttempt.request_id == req.request_id)
                    | (SubmissionAttempt.idempotency_key == req.idempotency_key)
                )
                .one_or_none()
            )
            if existing is None:
                raise RuntimeError(
                    "submission_attempt insert raced but row not found for request_id="
                    f"{req.request_id}"
                )
            result = _load_existing_result(session, existing)
            logger.info(
                "submission_attempt.ok workflow_id=%s run_id=%s case_id=%s attempt_id=%s status=%s outcome=%s receipt_artifact_id=%s manual_fallback_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                existing.submission_attempt_id,
                existing.status,
                existing.outcome,
                existing.receipt_artifact_id,
                result.manual_fallback_package_id,
            )
            return result
    except Exception as exc:
        logger.exception(
            "submission_attempt.error workflow_id=%s run_id=%s case_id=%s attempt_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.submission_attempt_id,
            req.request_id,
            type(exc).__name__,
        )

        try:
            with SessionLocal() as session:
                with session.begin():
                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is not None and attempt.status != "SUBMITTED":
                        attempt.status = "FAILED"
                        attempt.outcome = SubmissionAdapterOutcome.FAILED.value
                        attempt.failure_class = "ADAPTER_ERROR"
                        attempt.last_error = str(exc)
                        attempt.last_error_context = {
                            "request_id": req.request_id,
                            "exc_type": type(exc).__name__,
                        }
        except Exception:
            logger.exception(
                "submission_attempt.error_record_failed case_id=%s attempt_id=%s",
                req.case_id,
                req.submission_attempt_id,
            )
        raise


@activity.defn
def persist_correction_task(request: PersistCorrectionTaskRequest | dict) -> str:
    """Persist a correction task artifact with idempotent behavior."""

    req = PersistCorrectionTaskRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.correction_task_id,
    )

    requested_at = req.requested_at
    if requested_at and requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=dt.UTC)

    due_at = req.due_at
    if due_at and due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(CorrectionTask, req.correction_task_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.correction_task_id,
                        )
                        return req.correction_task_id

                    # Validate case and submission_attempt linkage
                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")

                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(
                            f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}"
                        )
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        CorrectionTask(
                            correction_task_id=req.correction_task_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            status=req.status,
                            summary=req.summary,
                            requested_at=requested_at,
                            due_at=due_at,
                        )
                    )

                logger.info(
                    "activity.ok name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.correction_task_id,
                )
                return req.correction_task_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(CorrectionTask, req.correction_task_id)
            if existing is None:
                raise RuntimeError(
                    f"correction_tasks insert raced but row not found for correction_task_id={req.correction_task_id}"
                )
            logger.info(
                "activity.ok name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.correction_task_id,
            )
            return req.correction_task_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.correction_task_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_resubmission_package(request: PersistResubmissionPackageRequest | dict) -> str:
    """Persist a resubmission package artifact with idempotent behavior."""

    req = PersistResubmissionPackageRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.resubmission_package_id,
    )

    submitted_at = req.submitted_at
    if submitted_at and submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(ResubmissionPackage, req.resubmission_package_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.resubmission_package_id,
                        )
                        return req.resubmission_package_id

                    # Validate case and submission_attempt linkage
                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")

                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(
                            f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}"
                        )
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        ResubmissionPackage(
                            resubmission_package_id=req.resubmission_package_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            package_id=req.package_id,
                            package_version=req.package_version,
                            status=req.status,
                            submitted_at=submitted_at,
                        )
                    )

                logger.info(
                    "activity.ok name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.resubmission_package_id,
                )
                return req.resubmission_package_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(ResubmissionPackage, req.resubmission_package_id)
            if existing is None:
                raise RuntimeError(
                    f"resubmission_packages insert raced but row not found for resubmission_package_id={req.resubmission_package_id}"
                )
            logger.info(
                "activity.ok name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.resubmission_package_id,
            )
            return req.resubmission_package_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.resubmission_package_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_approval_record(request: PersistApprovalRecordRequest | dict) -> str:
    """Persist an approval record artifact with idempotent behavior."""

    req = PersistApprovalRecordRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.approval_record_id,
    )

    decided_at = req.decided_at
    if decided_at and decided_at.tzinfo is None:
        decided_at = decided_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(ApprovalRecord, req.approval_record_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.approval_record_id,
                        )
                        return req.approval_record_id

                    # Validate case and submission_attempt linkage
                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")

                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(
                            f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}"
                        )
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        ApprovalRecord(
                            approval_record_id=req.approval_record_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            decision=req.decision,
                            authority=req.authority,
                            decided_at=decided_at,
                        )
                    )

                logger.info(
                    "activity.ok name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.approval_record_id,
                )
                return req.approval_record_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(ApprovalRecord, req.approval_record_id)
            if existing is None:
                raise RuntimeError(
                    f"approval_records insert raced but row not found for approval_record_id={req.approval_record_id}"
                )
            logger.info(
                "activity.ok name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.approval_record_id,
            )
            return req.approval_record_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.approval_record_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_inspection_milestone(request: PersistInspectionMilestoneRequest | dict) -> str:
    """Persist an inspection milestone artifact with idempotent behavior."""

    req = PersistInspectionMilestoneRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.inspection_milestone_id,
    )

    scheduled_for = req.scheduled_for
    if scheduled_for and scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=dt.UTC)

    completed_at = req.completed_at
    if completed_at and completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(InspectionMilestone, req.inspection_milestone_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.inspection_milestone_id,
                        )
                        return req.inspection_milestone_id

                    # Validate case and submission_attempt linkage
                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")

                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(
                            f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}"
                        )
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        InspectionMilestone(
                            inspection_milestone_id=req.inspection_milestone_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            milestone_type=req.milestone_type,
                            status=req.status,
                            scheduled_for=scheduled_for,
                            completed_at=completed_at,
                        )
                    )

                logger.info(
                    "activity.ok name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.inspection_milestone_id,
                )
                return req.inspection_milestone_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(InspectionMilestone, req.inspection_milestone_id)
            if existing is None:
                raise RuntimeError(
                    f"inspection_milestones insert raced but row not found for inspection_milestone_id={req.inspection_milestone_id}"
                )
            logger.info(
                "activity.ok name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.inspection_milestone_id,
            )
            return req.inspection_milestone_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.inspection_milestone_id,
            type(exc).__name__,
        )
        raise
