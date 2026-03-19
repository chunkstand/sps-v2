from __future__ import annotations

import hashlib
import uuid

import pytest

from sps.config import get_settings
from sps.storage.s3 import IntegrityError, S3Storage

pytestmark = pytest.mark.integration


def test_storage_adapter_put_head_presign_roundtrip():
    settings = get_settings()
    storage = S3Storage(settings)

    bucket = settings.s3_bucket_evidence
    storage.ensure_bucket(bucket)

    key = f"tests/{uuid.uuid4().hex}.bin"
    content = b"hello-minio"

    expected_sha = hashlib.sha256(content).hexdigest()

    put = storage.put_bytes(
        bucket=bucket,
        key=key,
        content=content,
        expected_sha256_hex=expected_sha,
        expected_bytes=len(content),
        content_type="application/octet-stream",
    )

    assert put.sha256_hex == expected_sha
    assert put.bytes == len(content)

    head = storage.head(bucket=bucket, key=key)
    assert head["ContentLength"] == len(content)

    url = storage.presign_get(bucket=bucket, key=key)
    assert "X-Amz-Signature" in url


def test_storage_adapter_rejects_sha_mismatch():
    settings = get_settings()
    storage = S3Storage(settings)

    bucket = settings.s3_bucket_evidence
    storage.ensure_bucket(bucket)

    key = f"tests/{uuid.uuid4().hex}.bin"
    content = b"hello-minio"

    with pytest.raises(IntegrityError):
        storage.put_bytes(
            bucket=bucket,
            key=key,
            content=content,
            expected_sha256_hex="0" * 64,
            expected_bytes=len(content),
        )
