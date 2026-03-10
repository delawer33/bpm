from __future__ import annotations

from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


def _get_client() -> Any:
    settings = get_settings()
    protocol = "https" if settings.minio_secure else "http"
    endpoint = f"{protocol}://{settings.minio_endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def build_tmp_key(user_id: str, track_id: str, filename: str) -> str:
    return f"tmp/{user_id}/{track_id}/{filename}"


def get_presigned_put_url(
    storage_key: str,
    expires_in: int | None = None,
) -> str:
    settings = get_settings()
    if expires_in is None:
        expires_in = settings.minio_presign_expire_seconds
    client = _get_client()
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.minio_bucket,
                "Key": storage_key,
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        # TODO log
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e
    return url
