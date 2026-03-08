import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis
from app.dependencies import get_current_user
from app.modules.tracks.schemas import STrackID, STrackUpload
from app.modules.tracks.services.track import TrackService
from app.modules.users.models import User

router = APIRouter(prefix="/tracks")


@router.post("/draft", response_model=STrackID)
async def create_draft_track(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    ts = TrackService(db)
    track = await ts.create_draft(current_user.id)
    return STrackID(track_id=track.id)


@router.post("/{id}/submit")
async def submit(
    id: uuid.UUID,
    data: STrackUpload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    ts = TrackService(db, redis_client)
    track = await ts.create_track(data, id, current_user.id)
    return JSONResponse({"message": "ok"})
