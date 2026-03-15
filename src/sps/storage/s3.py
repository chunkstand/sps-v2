from __future__ import annotations

import hashlib
from dataclasses import dataclass

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from sps.config import Settings


class StorageError(RuntimeError):
    pass


class IntegrityError(StorageError):
    pass


@dataclass(frozen=True)
class PutResult:
    bucket: str
    key: str
    bytes: int
    sha256_hex: str
    etag: str | None


class S3Storage:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=BotoConfig(signature_version="s3v4"),
        )

    def ensure_bucket(self, bucket: str) -> None:
        try:
            self._client.head_bucket(Bucket=bucket)
            return
        except ClientError as e:
            code = (e.response or {}).get("Error", {}).get("Code")
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise StorageError(f"S3 head_bucket failed for {bucket}: {code}") from e

        try:
            self._client.create_bucket(Bucket=bucket)
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"S3 create_bucket failed for {bucket}") from e

    def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        content: bytes,
        expected_sha256_hex: str | None = None,
        expected_bytes: int | None = None,
        content_type: str | None = None,
    ) -> PutResult:
        actual_bytes = len(content)
        actual_sha = hashlib.sha256(content).hexdigest()

        if expected_bytes is not None and expected_bytes != actual_bytes:
            raise IntegrityError(
                f"Byte length mismatch for s3://{bucket}/{key}: expected {expected_bytes}, got {actual_bytes}"
            )
        if expected_sha256_hex is not None and expected_sha256_hex.lower() != actual_sha.lower():
            raise IntegrityError(
                f"sha256 mismatch for s3://{bucket}/{key}: expected {expected_sha256_hex}, got {actual_sha}"
            )

        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            resp = self._client.put_object(Bucket=bucket, Key=key, Body=content, **extra_args)
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"S3 put_object failed for s3://{bucket}/{key}") from e

        etag = resp.get("ETag")
        return PutResult(bucket=bucket, key=key, bytes=actual_bytes, sha256_hex=actual_sha, etag=etag)

    def head(self, *, bucket: str, key: str) -> dict:
        try:
            return self._client.head_object(Bucket=bucket, Key=key)
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"S3 head_object failed for s3://{bucket}/{key}") from e

    def presign_get(self, *, bucket: str, key: str) -> str:
        try:
            return self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=self._settings.s3_presign_expires_seconds,
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"S3 presign GET failed for s3://{bucket}/{key}") from e
