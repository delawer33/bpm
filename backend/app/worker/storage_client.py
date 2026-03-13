from __future__ import annotations

from typing import Any

from app.core.storage import create_s3_client

_client: Any | None = None


def get_storage_client() -> Any:
    if _client is None:
        raise RuntimeError("Storage client not initialized")
    return _client


def init_storage_client(client: Any | None = None) -> None:
    global _client
    if client is not None:
        _client = client
        return
    _client = create_s3_client()


def reset_storage_client(client: Any | None = None) -> None:
    global _client
    if client is not None:
        _client = client
        return
    _client = create_s3_client()

