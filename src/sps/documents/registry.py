"""Evidence registry for document and manifest artifact storage with sha256 validation."""
from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass

from sps.config import Settings
from sps.evidence.ids import evidence_object_key, new_evidence_id
from sps.evidence.models import ArtifactClass, RetentionClass
from sps.storage.s3 import S3Storage


@dataclass(frozen=True)
class RegisteredArtifact:
    """Result from evidence registration with artifact_id and validated digest."""
    
    artifact_id: str
    sha256_digest: str
    content_bytes: int
    storage_uri: str


class EvidenceRegistry:
    """Helper for registering evidence artifacts with sha256 validation."""
    
    def __init__(self, storage: S3Storage, settings: Settings):
        self._storage = storage
        self._settings = settings
    
    def register_document(
        self,
        *,
        content: bytes,
        case_id: str,
        document_type: str,
        provenance: dict | None = None,
    ) -> RegisteredArtifact:
        """
        Register a document artifact in the evidence registry.
        
        Uploads content to S3 with sha256 validation and returns artifact ID + digest.
        """
        artifact_id = new_evidence_id()
        object_key = evidence_object_key(artifact_id)
        
        # Compute digest before upload
        sha256_digest = hashlib.sha256(content).hexdigest()
        
        # Upload with integrity check
        result = self._storage.put_bytes(
            bucket=self._settings.s3_bucket_evidence,
            key=object_key,
            content=content,
            expected_sha256_hex=sha256_digest,
            content_type="text/plain",
        )
        
        storage_uri = f"s3://{result.bucket}/{result.key}"
        
        return RegisteredArtifact(
            artifact_id=artifact_id,
            sha256_digest=result.sha256_hex,
            content_bytes=result.bytes,
            storage_uri=storage_uri,
        )
    
    def register_manifest(
        self,
        *,
        content: bytes,
        case_id: str,
        provenance: dict | None = None,
    ) -> RegisteredArtifact:
        """
        Register a manifest artifact in the evidence registry.
        
        Uploads content to S3 with sha256 validation and returns artifact ID + digest.
        """
        artifact_id = new_evidence_id()
        object_key = evidence_object_key(artifact_id)
        
        # Compute digest before upload
        sha256_digest = hashlib.sha256(content).hexdigest()
        
        # Upload with integrity check
        result = self._storage.put_bytes(
            bucket=self._settings.s3_bucket_evidence,
            key=object_key,
            content=content,
            expected_sha256_hex=sha256_digest,
            content_type="application/json",
        )
        
        storage_uri = f"s3://{result.bucket}/{result.key}"
        
        return RegisteredArtifact(
            artifact_id=artifact_id,
            sha256_digest=result.sha256_hex,
            content_bytes=result.bytes,
            storage_uri=storage_uri,
        )
