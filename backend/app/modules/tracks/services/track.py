import uuid
from typing import Dict, List

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.track_meta import resolve_slugs
from app.modules.tracks.exceptions import (
    InvalidGenreError,
    InvalidInstrumentError,
    InvalidMoodError,
)
from app.modules.tracks.models.track import Track


class TrackService:
    def __init__(self, db: AsyncSession, redis_client: Redis) -> None:
        self.db = db
        self.redis_client = redis_client

    async def create_draft(self, user_id: uuid.UUID) -> Track:
        track = Track(user_id=user_id)
        self.db.add(track)
        await self.db.flush()
        return track


async def validate_slugs(
    redis: Redis, genre_slug: str, mood_slugs: List[str], instrument_slugs: List[str]
) -> Dict[str, List[int] | int]:
    try:
        genre_ids = await resolve_slugs(redis, "genres", [genre_slug])
    except ValueError:
        raise InvalidGenreError
    try:
        mood_ids = await resolve_slugs(redis, "moods", mood_slugs)
    except ValueError:
        raise InvalidMoodError
    try:
        instrument_ids = await resolve_slugs(redis, "instruments", instrument_slugs)
    except ValueError:
        raise InvalidInstrumentError

    return {"genre_ids": genre_ids, "mood_ids": mood_ids, "instrument_ids": instrument_ids}
