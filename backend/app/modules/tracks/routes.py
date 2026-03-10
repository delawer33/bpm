import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis
from app.dependencies import get_current_user
from app.modules.tracks.schemas import (
    STrackFileUploadRequest,
    STrackFileUploadResponse,
    STrackID,
    STrackOwnerResponse,
    STrackUpload,
)
from app.modules.tracks.services.track import TrackService
from app.modules.tracks.services.track_file import TrackFileService
from app.modules.users.models import User

router = APIRouter(prefix="/tracks")

FileTypePath = Literal["preview", "main", "stems", "image"]


@router.post("/draft", response_model=STrackID)
async def create_draft_track(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    ts = TrackService(db)
    track = await ts.create_draft(current_user.id)
    return STrackID(track_id=track.id)


@router.post("/{track_id}/submit")
async def submit(
    track_id: uuid.UUID,
    data: STrackUpload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    ts = TrackService(db, redis_client)
    track = await ts.create_track(data, track_id, current_user.id)
    return JSONResponse({"message": "ok"})


@router.post(
    "/{track_id}/files/{file_type}",
    response_model=STrackFileUploadResponse,
)
async def create_track_file_upload_url(
    track_id: uuid.UUID,
    file_type: FileTypePath,
    data: STrackFileUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tfs = TrackFileService(db)
    upload_url = await tfs.get_presigned_upload(
        track_id=track_id,
        file_type_lit=file_type,
        user_id=current_user.id,
        filename=data.filename,
        size=data.size,
        mime=data.mime,
    )
    await db.commit()
    return STrackFileUploadResponse(uploadUrl=upload_url)


@router.get("/{track_id}", response_model=STrackOwnerResponse)
async def get_track_for_owner(
    track_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ts = TrackService(db)
    track = await ts.get_track_by_id(track_id, current_user.id)
    return track
