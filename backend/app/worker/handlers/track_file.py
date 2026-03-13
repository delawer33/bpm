from __future__ import annotations

import asyncio
import tempfile
import uuid
import zipfile
from pathlib import Path

import librosa
from PIL import Image
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
from app.modules.users.models import User # noqa: needed when working with track
from app.modules.tracks.models.track import Track
from app.modules.tracks.models.track_file import TrackFile, TrackFileStatus, TrackFileType
from app.modules.tracks.models.thumbnail import Thumbnail
from app.modules.tracks.services.track import TrackService
from app.modules.tracks.services.track_file import _get_max_size
from app.utils.get_volume_tags import extract_volume_tags
from app.worker.constants import MAX_THUMBNAIL_PX, WAVEFORM_NUM_TAGS
from app.worker.parsers import parse_tmp_storage_key
from app.worker.storage_client import get_storage_client
from app.logger_settings import logger


async def handle_track_file_upload(
    session: AsyncSession,
    bucket: str,
    key: str,
) -> None:
    parsed = parse_tmp_storage_key(key)
    if not parsed:
        logger.warning("Invalid tmp key format: %s", key)
        return
    user_id, track_uuid, filename = parsed

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
        await asyncio.to_thread(get_object_to_file, key, tmp_path, client=get_storage_client())
        permanent_key = build_tracks_key(user_id, str(track_uuid), filename)
        await asyncio.to_thread(copy_object, key, permanent_key, client=get_storage_client())
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
        logger.error("Processing failed for %s: %s", key, e)
        await _mark_track_file_failed_and_commit(session, track_uuid, track_file.id)
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


async def _mark_track_file_failed_and_commit(
    session: AsyncSession,
    track_id: uuid.UUID,
    track_file_id: uuid.UUID,
) -> None:
    await session.rollback()
    result = await session.execute(select(TrackFile).where(TrackFile.id == track_file_id))
    tf = result.scalar_one_or_none()
    if tf:
        tf.status = TrackFileStatus.FAILED
        ts = TrackService(session)
        await ts.update_track_status_for_files(track_id)
    await session.commit()


def _compute_audio_metadata_sync(path: str, num_tags: int) -> tuple[int, list[float]]:
    y, sr = librosa.load(path, sr=22050, mono=True)
    duration_seconds = int(len(y) / sr)
    tags = extract_volume_tags(path, num_tags=num_tags)
    return duration_seconds, tags.tolist()


async def _process_audio(
    session: AsyncSession,
    track_file: TrackFile,
    track_id: uuid.UUID,
    path: str,
) -> None:
    try:
        duration_seconds, waveform_data = await asyncio.to_thread(
            _compute_audio_metadata_sync, path, WAVEFORM_NUM_TAGS
        )
        track_file.duration_seconds = duration_seconds
        if track_file.file_type == TrackFileType.PREVIEW.value:
            track = await session.get(Track, track_id)
            if track:
                track.waveform_data = waveform_data
        track_file.status = TrackFileStatus.READY
    except Exception as e:
        logger.warning("Audio processing failed for %s: %s", track_file.id, e)
        track_file.status = TrackFileStatus.FAILED
        raise


def _resize_and_save_thumbnail_sync(
    image_path: str, max_px: int
) -> tuple[str, int, int, str]:
    img = Image.open(image_path)
    img.load()
    w, h = img.size
    if w > max_px or h > max_px:
        ratio = min(max_px / w, max_px / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        new_w, new_h = w, h
    ext = "png" if img.mode in ("RGBA", "P") else "jpeg"
    content_type = f"image/{ext}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        thumb_path = tmp.name
        img.save(thumb_path, format="PNG" if ext == "png" else "JPEG", quality=85)
    return thumb_path, new_w, new_h, content_type


async def _process_image(
    session: AsyncSession,
    track_file: TrackFile,
    track_id: uuid.UUID,
    user_id: str,
    path: str,
) -> None:
    thumb_path = None
    try:
        thumb_path, new_w, new_h, content_type = await asyncio.to_thread(
            _resize_and_save_thumbnail_sync, path, MAX_THUMBNAIL_PX
        )
        thumb_filename = f"image_512.{content_type.split('/')[-1]}"
        thumb_key = build_thumbnail_key(user_id, str(track_id), thumb_filename)
        await asyncio.to_thread(
            put_object_from_file,
            thumb_key,
            thumb_path,
            content_type=content_type,
            client=get_storage_client(),
        )
    except Exception as e:
        logger.warning("Image/thumbnail processing failed for %s: %s", track_file.id, e)
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
