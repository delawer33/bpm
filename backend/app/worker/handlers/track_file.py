from __future__ import annotations

import librosa
from PIL import Image
import logging
import tempfile
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.storage import (
    build_thumbnail_key,
    build_tracks_key,
    copy_object,
    get_object_to_file,
    put_object_from_file,
)
from app.modules.users.models import User
from app.modules.tracks.models.track import Track
from app.modules.tracks.models.track_file import TrackFile, TrackFileStatus, TrackFileType
from app.modules.tracks.models.thumbnail import Thumbnail
from app.modules.tracks.services.track import TrackService
from app.modules.tracks.services.track_file import _get_max_size
from app.utils.get_volume_tags import extract_volume_tags

# logger = logging.getLogger("app_logger")
from app.logger_settings import logger
MAX_THUMBNAIL_PX = 512


async def handle_track_file_upload(
    session: AsyncSession,
    bucket: str,
    key: str,
) -> None:
    if not key.startswith("tmp/"):
        return
    parts = key.split("/")
    if len(parts) < 4:
        logger.warning("Invalid tmp key format: %s", key)
        return
    _prefix, user_id, track_id_str, filename = parts[0], parts[1], parts[2], "/".join(parts[3:])
    try:
        track_uuid = uuid.UUID(track_id_str)
    except ValueError:
        logger.warning("Invalid track_id in key: %s", key)
        return

    result = await session.execute(select(TrackFile).where(TrackFile.storage_key == key))
    track_file = result.scalar_one_or_none()
    if not track_file:
        logger.debug("No TrackFile for key %s", key)
        return
    if track_file.status == TrackFileStatus.READY:
        return
    if track_file.status == TrackFileStatus.FAILED:
        return
    track_file.status = TrackFileStatus.PROCESSING
    await session.flush()

    settings = get_settings()
    if bucket != settings.minio_bucket:
        await _mark_failed(session, track_file, track_uuid, "wrong bucket")
        await session.commit()
        return

    max_size = _get_max_size(TrackFileType(track_file.file_type))
    if track_file.file_size is not None and track_file.file_size > max_size:
        await _mark_failed(session, track_file, track_uuid, "file size exceeds limit")
        await session.commit()
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
        tmp_path = tmp.name
    try:
        get_object_to_file(key, tmp_path)
        permanent_key = build_tracks_key(user_id, str(track_uuid), filename)
        copy_object(key, permanent_key)
        track_file.storage_key = permanent_key

        if track_file.file_type in (TrackFileType.PREVIEW.value, TrackFileType.MAIN.value):
            await _process_audio(session, track_file, track_uuid, tmp_path)
        elif track_file.file_type == TrackFileType.IMAGE.value:
            await _process_image(session, track_file, track_uuid, user_id, tmp_path)
        elif track_file.file_type == TrackFileType.STEMS.value:
            if not zipfile.is_zipfile(tmp_path):
                await _mark_failed(session, track_file, track_uuid, "invalid zip")
                await session.commit()
                return
            track_file.status = TrackFileStatus.READY
        else:
            track_file.status = TrackFileStatus.READY

        ts = TrackService(session)
        await ts.update_track_status_for_files(track_uuid)
        await session.commit()
    except Exception as e:
        logger.exception("Processing failed for %s: %s", key, e)
        tf_id = track_file.id
        await session.rollback()
        result = await session.execute(select(TrackFile).where(TrackFile.id == tf_id))
        tf = result.scalar_one_or_none()
        if tf:
            tf.status = TrackFileStatus.FAILED
            ts = TrackService(session)
            await ts.update_track_status_for_files(track_uuid)
            await session.commit()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _mark_failed(
    session: AsyncSession,
    track_file: TrackFile,
    track_id: uuid.UUID,
    reason: str,
) -> None:
    track_file.status = TrackFileStatus.FAILED
    logger.warning("Marking TrackFile %s failed: %s", track_file.id, reason)
    ts = TrackService(session)
    await ts.update_track_status_for_files(track_id)


async def _process_audio(
    session: AsyncSession,
    track_file: TrackFile,
    track_id: uuid.UUID,
    path: str,
) -> None:
    try:
        y, sr = librosa.load(path, sr=22050, mono=True)
        duration_seconds = int(len(y) / sr)
        track_file.duration_seconds = duration_seconds
        if track_file.file_type == TrackFileType.PREVIEW.value:
            tags = extract_volume_tags(path, num_tags=300)
            waveform_data = tags.tolist()
            track = await session.get(Track, track_id)
            if track:
                track.waveform_data = waveform_data
        track_file.status = TrackFileStatus.READY
    except Exception as e:
        logger.warning("Audio processing failed for %s: %s", track_file.id, e)
        track_file.status = TrackFileStatus.FAILED
        raise


async def _process_image(
    session: AsyncSession,
    track_file: TrackFile,
    track_id: uuid.UUID,
    user_id: str,
    path: str,
) -> None:
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        logger.warning("Image open failed for %s: %s", track_file.id, e)
        track_file.status = TrackFileStatus.FAILED
        raise

    w, h = img.size
    if w > MAX_THUMBNAIL_PX or h > MAX_THUMBNAIL_PX:
        ratio = min(MAX_THUMBNAIL_PX / w, MAX_THUMBNAIL_PX / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        new_w, new_h = w, h

    ext = "png" if img.mode in ("RGBA", "P") else "jpeg"
    thumb_filename = f"image_512.{ext}"
    thumb_key = build_thumbnail_key(user_id, str(track_id), thumb_filename)
    thumb_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            thumb_path = tmp.name
            img.save(thumb_path, format="PNG" if ext == "png" else "JPEG", quality=85)
        put_object_from_file(thumb_key, thumb_path, content_type=f"image/{ext}")
    except Exception as e:
        logger.warning("Thumbnail upload failed for %s: %s", track_file.id, e)
        track_file.status = TrackFileStatus.FAILED
        raise
    finally:
        if thumb_path:
            Path(thumb_path).unlink(missing_ok=True)

    existing = (await session.execute(select(Thumbnail).where(Thumbnail.track_id == track_id))).scalars().all()
    for t in existing:
        await session.delete(t)
    thumb = Thumbnail(
        track_id=track_id,
        storage_key=thumb_key,
        width=new_w,
        height=new_h,
    )
    session.add(thumb)
    track_file.status = TrackFileStatus.READY
