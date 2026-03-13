import logging
import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.storage import (
    build_tmp_key,
    get_presigned_get_url,
    get_presigned_put_url,
)
from app.modules.tracks.exceptions import TrackFileValidationError, TrackNotFoundOrNoAccessError
from app.modules.tracks.models.track import Track, TrackVisibility
from app.modules.tracks.models.track_file import TrackFile, TrackFileStatus, TrackFileType

logger = logging.getLogger("app_logger")

ALLOWED_MIMES: dict[TrackFileType, frozenset[str]] = {
    TrackFileType.PREVIEW: frozenset({"audio/mpeg", "audio/wav", "audio/x-wav"}),
    TrackFileType.MAIN: frozenset({"audio/mpeg", "audio/wav", "audio/x-wav"}),
    TrackFileType.STEMS: frozenset({"application/zip"}),
    TrackFileType.IMAGE: frozenset({"image/png", "image/jpeg"}),
}

TYPE_FILENAMES: dict[TrackFileType, str] = {
    TrackFileType.PREVIEW: "preview.mp3",
    TrackFileType.MAIN: "main.wav",
    TrackFileType.STEMS: "stems.zip",
    TrackFileType.IMAGE: "image.png",
}


def _get_max_size(file_type: TrackFileType) -> int:
    settings = get_settings()
    if file_type == TrackFileType.PREVIEW:
        return settings.minio_max_preview_bytes
    if file_type == TrackFileType.MAIN:
        return settings.minio_max_main_bytes
    if file_type == TrackFileType.STEMS:
        return settings.minio_max_stems_bytes
    if file_type == TrackFileType.IMAGE:
        return settings.minio_max_image_bytes
    raise ValueError(f"Unknown file type: {file_type}")


def _validate_mime_and_size(
    file_type: TrackFileType,
    mime: str,
    size: int,
) -> None:
    allowed = ALLOWED_MIMES.get(file_type)
    if not allowed or mime not in allowed:
        raise TrackFileValidationError(f"Invalid mime for {file_type.value}: {mime}")
    max_size = _get_max_size(file_type)
    if size > max_size:
        raise TrackFileValidationError(
            f"File size exceeds max {max_size} bytes for {file_type.value}"
        )


FileTypeLiteral = Literal["preview", "main", "stems", "image"]

FILE_TYPE_MAP: dict[FileTypeLiteral, TrackFileType] = {
    "preview": TrackFileType.PREVIEW,
    "main": TrackFileType.MAIN,
    "stems": TrackFileType.STEMS,
    "image": TrackFileType.IMAGE,
}


class TrackFileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_presigned_upload(
        self,
        track_id: uuid.UUID,
        file_type_lit: FileTypeLiteral,
        user_id: uuid.UUID,
        filename: str,
        size: int,
        mime: str,
        *,
        client: Any | None = None,
    ) -> str:
        track = await self.db.scalar(select(Track).where(Track.id == track_id))
        if not track:
            raise TrackNotFoundOrNoAccessError
        if str(track.user_id) != str(user_id):
            raise TrackNotFoundOrNoAccessError

        file_type = FILE_TYPE_MAP[file_type_lit]
        _validate_mime_and_size(file_type, mime, size)

        filename_for_key = TYPE_FILENAMES[file_type]
        storage_key = build_tmp_key(str(user_id), str(track_id), filename_for_key)

        existing = await self.db.scalar(
            select(TrackFile).where(
                TrackFile.track_id == track_id,
                TrackFile.file_type == file_type.value,
            )
        )
        if existing:
            existing.storage_key = storage_key
            existing.file_name = filename
            existing.file_size = size
            existing.mime_type = mime
            existing.status = TrackFileStatus.PENDING
            track_file = existing
        else:
            track_file = TrackFile(
                track_id=track_id,
                file_type=file_type,
                status=TrackFileStatus.PENDING,
                storage_key=storage_key,
                file_name=filename,
                file_size=size,
                mime_type=mime,
            )
            self.db.add(track_file)

        await self.db.flush()
        upload_url = get_presigned_put_url(storage_key, client=client)
        return upload_url

    async def get_track_file_for_user(
        self,
        track_file_id: uuid.UUID,
        current_user_id: uuid.UUID,
        s3_client: Any,
    ) -> tuple[TrackFile, str]:
        stmt = (
            select(TrackFile)
            .options(selectinload(TrackFile.track))
            .where(TrackFile.id == track_file_id)
        )
        result = await self.db.execute(stmt)
        track_file = result.scalar_one_or_none()
        if not track_file or not track_file.track:
            raise TrackNotFoundOrNoAccessError

        track = track_file.track

        if str(track.user_id) != str(current_user_id):
            if track.visibility is not TrackVisibility.PUBLIC:
                raise TrackNotFoundOrNoAccessError
            if track_file.file_type not in {TrackFileType.PREVIEW.value, TrackFileType.IMAGE.value}:
                raise TrackNotFoundOrNoAccessError

        url = get_presigned_get_url(track_file.storage_key, client=s3_client)
        return track_file, url
