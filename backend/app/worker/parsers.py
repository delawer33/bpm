from __future__ import annotations

import json
import uuid
from typing import Any
import urllib.parse


class StorageEvent:
    __slots__ = ("bucket", "key")

    def __init__(self, bucket: str, key: str) -> None:
        self.bucket = bucket
        self.key = key


def parse_storage_event(body: bytes) -> StorageEvent | None:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    records = data.get("Records") or data.get("Event") or []
    if isinstance(records, dict):
        records = [records]
    if not records:
        return None
    first: Any = records[0]
    s3 = first.get("s3") or first.get("S3") or {}
    if isinstance(s3, str):
        return None
    bucket = (s3.get("bucket") or {}).get("name") or (s3.get("bucket") or {}).get("Name")
    obj = s3.get("object") or s3.get("Object") or {}
    key = obj.get("key") or obj.get("Key")
    if not bucket or not key:
        return None
    key = urllib.parse.unquote(key)
    return StorageEvent(bucket=str(bucket), key=str(key))


def parse_tmp_storage_key(key: str) -> tuple[str, uuid.UUID, str] | None:
    """
    Parse a tmp storage key into (user_id, track_id, filename).
    Key must be of the form: tmp/{user_id}/{track_id}/{filename}
    """
    if not key.startswith("tmp/"):
        return None
    parts = key.split("/")
    if len(parts) < 4:
        return None
    user_id = parts[1]
    track_id_str = parts[2]
    filename = "/".join(parts[3:])
    try:
        track_id = uuid.UUID(track_id_str)
    except ValueError:
        return None
    return user_id, track_id, filename
