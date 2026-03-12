from __future__ import annotations

import json
from typing import Any
import urllib.parse


def parse_storage_event(body: bytes) -> tuple[str, str] | None:
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
    return str(bucket), str(key)
