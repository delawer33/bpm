from __future__ import annotations

from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


def create_s3_client() -> Any:
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


def _get_client() -> Any:
    return create_s3_client()


def build_tmp_key(user_id: str, track_id: str, filename: str) -> str:
    return f"tmp/{user_id}/{track_id}/{filename}"


def build_tracks_key(user_id: str, track_id: str, filename: str) -> str:
    return f"tracks/{user_id}/{track_id}/{filename}"


def build_thumbnail_key(user_id: str, track_id: str, filename: str) -> str:
    return f"thumbnails/{user_id}/{track_id}/{filename}"


def copy_object(source_key: str, dest_key: str, *, client: Any | None = None) -> None:
    settings = get_settings()
    if client is None:
        client = _get_client()
    client.copy_object(
        Bucket=settings.minio_bucket,
        CopySource={"Bucket": settings.minio_bucket, "Key": source_key},
        Key=dest_key,
    )


def get_object_to_file(storage_key: str, path: str, *, client: Any | None = None) -> None:
    settings = get_settings()
    if client is None:
        client = _get_client()
    client.download_file(settings.minio_bucket, storage_key, path)


def put_object_from_file(
    storage_key: str,
    path: str,
    content_type: str | None = None,
    *,
    client: Any | None = None,
) -> None:
    settings = get_settings()
    if client is None:
        client = _get_client()
    extra: dict[str, str] = {}
    if content_type:
        extra["ContentType"] = content_type
    client.upload_file(path, settings.minio_bucket, storage_key, ExtraArgs=extra)


def get_presigned_put_url(
    storage_key: str,
    expires_in: int | None = None,
    *,
    client: Any | None = None,
) -> str:
    settings = get_settings()
    if expires_in is None:
        expires_in = settings.minio_presign_expire_seconds
    if client is None:
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
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e
    return url


def get_presigned_get_url(
    storage_key: str,
    expires_in: int | None = None,
    *,
    client: Any | None = None,
) -> str:
    settings = get_settings()
    if expires_in is None:
        expires_in = settings.minio_presign_expire_seconds
    if client is None:
        client = _get_client()
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.minio_bucket,
                "Key": storage_key,
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e
    return url
