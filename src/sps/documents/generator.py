"""Document generator for deterministic submission packages from templates."""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from sps.adapters.contracts import DocumentCompilationSpec, DocumentTemplateSpec
from sps.documents.contracts import (
    DocumentArtifactPayload,
    DocumentType,
    ManifestDocumentReference,
    SubmissionManifestPayload,
    SubmissionPackagePayload,
)
from sps.evidence.ids import new_evidence_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedDocument:
    """Result from document template rendering."""
    
    document_id: str
    document_type: DocumentType
    template_name: str
    content_bytes: bytes
    sha256_digest: str
    variables: dict[str, str | int | float | bool]


def _render_template(template_content: str, variables: dict) -> str:
    """
    Render mustache-style {{variable}} placeholders in template.
    
    Simple string replacement — sufficient for deterministic fixture rendering.
    For production templates, consider a proper template engine (Jinja2, mustache.py).
    """
    rendered = template_content
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        rendered = rendered.replace(placeholder, str(value))
    
    # Check for unreplaced placeholders
    unreplaced = re.findall(r'\{\{([^}]+)\}\}', rendered)
    if unreplaced:
        logger.warning(
            "generator.unreplaced_placeholders template=%s placeholders=%s",
            "template",
            unreplaced,
        )
    
    return rendered


def _load_template(template_path: Path) -> str:
    return template_path.read_text(encoding="utf-8")


def generate_document(definition: DocumentTemplateSpec, *, case_id: str) -> GeneratedDocument:
    """
    Generate a single document from a fixture definition.
    
    Args:
        definition: Document definition with template name and variables
        case_id: Runtime case ID to inject into variables
        
    Returns:
        GeneratedDocument with rendered bytes and sha256 digest
    """
    # Load template content
    template_content = _load_template(definition.template_path)
    
    # Merge runtime case_id with fixture variables
    variables = {**definition.variables, "case_id": case_id}
    
    # Render template
    rendered_text = _render_template(template_content, variables)
    content_bytes = rendered_text.encode("utf-8")
    
    # Compute sha256 digest
    sha256_digest = hashlib.sha256(content_bytes).hexdigest()
    
    logger.info(
        "generator.document_rendered document_id=%s document_type=%s template=%s bytes=%d digest=%s",
        definition.document_id,
        definition.document_type,
        definition.template_name,
        len(content_bytes),
        sha256_digest,
    )
    
    return GeneratedDocument(
        document_id=definition.document_id,
        document_type=DocumentType(definition.document_type),
        template_name=definition.template_name,
        content_bytes=content_bytes,
        sha256_digest=sha256_digest,
        variables=variables,
    )


def build_manifest_payload(
    *,
    case_id: str,
    generated_documents: list[tuple[GeneratedDocument, str]],
    package_version: str,
    target_portal_family: str,
    required_attachments: list[str] | None = None,
) -> SubmissionManifestPayload:
    """
    Build manifest payload from generated documents with artifact IDs.
    
    Args:
        case_id: Case identifier
        generated_documents: List of (GeneratedDocument, artifact_id) tuples
        package_version: Package version string
        target_portal_family: Portal family identifier
        required_attachments: Optional list of required attachment names
        
    Returns:
        SubmissionManifestPayload with document references
    """
    manifest_id = new_evidence_id()
    generated_at = dt.datetime.now(dt.UTC)
    
    document_references = [
        ManifestDocumentReference(
            document_id=doc.document_id,
            document_type=doc.document_type,
            artifact_id=artifact_id,
            sha256_digest=doc.sha256_digest,
        )
        for doc, artifact_id in generated_documents
    ]
    
    manifest = SubmissionManifestPayload(
        manifest_id=manifest_id,
        case_id=case_id,
        package_version=package_version,
        generated_at=generated_at,
        document_references=document_references,
        required_attachments=required_attachments or [],
        target_portal_family=target_portal_family,
        provenance={
            "generator": "sps.documents.generator",
            "schema_version": "1.0.0",
        },
    )
    
    logger.info(
        "generator.manifest_built manifest_id=%s case_id=%s doc_count=%d",
        manifest_id,
        case_id,
        len(document_references),
    )
    
    return manifest


def generate_submission_package(
    compilation: DocumentCompilationSpec,
    *,
    runtime_case_id: str,
) -> SubmissionPackagePayload:
    """
    Generate complete submission package from fixture definition.
    
    This is the high-level orchestrator:
    1. Generate each document from its template + variables
    2. Build manifest with document references
    3. Assemble package payload
    
    Args:
        fixture: Document set fixture with templates and manifest structure
        runtime_case_id: Runtime case ID (may differ from fixture.case_id if override used)
        
    Returns:
        SubmissionPackagePayload ready for persistence + evidence registration
    """
    logger.info(
        "generator.package_start case_id=%s fixture_case_id=%s doc_count=%d",
        runtime_case_id,
        compilation.case_id,
        len(compilation.documents),
    )
    
    # Generate documents
    generated_docs: list[GeneratedDocument] = []
    for doc_def in compilation.documents:
        generated = generate_document(doc_def, case_id=runtime_case_id)
        generated_docs.append(generated)
    
    # Assign artifact IDs (to be used when registering evidence)
    # These are deterministic pre-allocated IDs — the actual artifact_id will come
    # from evidence registry during persistence
    docs_with_artifact_ids = [(doc, new_evidence_id()) for doc in generated_docs]
    
    # Build manifest
    manifest = build_manifest_payload(
        case_id=runtime_case_id,
        generated_documents=docs_with_artifact_ids,
        package_version=compilation.package_version,
        target_portal_family=compilation.target_portal_family,
        required_attachments=compilation.required_attachments,
    )
    
    # Compute manifest digest from JSON bytes
    manifest_json = manifest.model_dump_json(exclude_none=True, indent=None)
    manifest_bytes = manifest_json.encode("utf-8")
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    
    # Build document artifact payloads
    document_artifacts = [
        DocumentArtifactPayload(
            document_id=doc.document_id,
            document_type=doc.document_type,
            case_id=runtime_case_id,
            template_name=doc.template_name,
            content_bytes=doc.content_bytes,
            sha256_digest=doc.sha256_digest,
            generated_at=manifest.generated_at,
            provenance={
                "template_name": doc.template_name,
                "variables": list(doc.variables.keys()),
            },
        )
        for doc, artifact_id in docs_with_artifact_ids
    ]
    
    package = SubmissionPackagePayload(
        package_id=new_evidence_id(),
        case_id=runtime_case_id,
        package_version=compilation.package_version,
        manifest=manifest,
        document_artifacts=document_artifacts,
        manifest_sha256_digest=manifest_digest,
        created_at=dt.datetime.now(dt.UTC),
        provenance={
            "document_set_id": compilation.document_set_id,
            "generator": "sps.documents.generator.generate_submission_package",
        },
    )
    
    logger.info(
        "generator.package_complete package_id=%s case_id=%s manifest_id=%s manifest_digest=%s doc_count=%d",
        package.package_id,
        runtime_case_id,
        manifest.manifest_id,
        manifest_digest,
        len(document_artifacts),
    )
    
    return package
