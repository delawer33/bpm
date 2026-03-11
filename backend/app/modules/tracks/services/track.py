import logging
import uuid

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache.track_meta import resolve_slugs
from app.modules.tracks.exceptions import (
    InvalidVisibilityStatusError,
    SlugValidationError,
    TrackNotFoundError,
    TrackNotFoundOrNoAccessError,
)
from app.modules.tracks.models.genre import Genre
from app.modules.tracks.models.instrument import Instrument
from app.modules.tracks.models.mood import Mood
from app.modules.tracks.models.tag import Tag
from app.modules.tracks.models.track import Track, TrackVisibility
from app.modules.tracks.schemas import STrackUpload

logger = logging.getLogger("app_logger")


class TrackService:
    def __init__(self, db: AsyncSession, redis_client: Redis | None = None) -> None:
        self.db = db
        self.redis_client = redis_client

    async def create_draft(self, user_id: uuid.UUID) -> Track:
        track = Track(user_id=user_id)
        self.db.add(track)
        await self.db.flush()
        return track

    async def get_track_full(self, track_id: uuid.UUID, user_id: uuid.UUID) -> Track:
        stmt = await self.db.execute(
            select(Track)
            .where(Track.id == track_id, Track.user_id == user_id)
            .options(
                selectinload(Track.tags),
                selectinload(Track.genres),
                selectinload(Track.moods),
                selectinload(Track.instruments),
                selectinload(Track.files),
            )
        )
        track = stmt.scalar_one_or_none()
        if not track:
            raise TrackNotFoundError
        return track

    async def create_track(self, track_data: STrackUpload, track_id: uuid.UUID, user_id: uuid.UUID):
        if not self.redis_client:
            raise RuntimeError("Redis client is required for slug validation")

        payload = track_data.model_dump()

        track = await self.db.scalar(
            select(Track)
            .options(
                selectinload(Track.tags),
                selectinload(Track.genres),
                selectinload(Track.moods),
                selectinload(Track.instruments),
            )
            .where(Track.id == track_id)
        )
        if not track or track.user_id != user_id:
            raise TrackNotFoundOrNoAccessError

        try:
            visibility = TrackVisibility(payload["visibility"])
        except ValueError:
            raise InvalidVisibilityStatusError

        track.visibility = visibility
        genre_slugs = payload.pop("genres", [])
        mood_slugs = payload.pop("moods", [])
        instrument_slugs = payload.pop("instruments", [])
        track.title = payload["title"]
        track.description = payload.get("description")
        track.bpm = payload["bpm"]
        track.root_note = payload["root_note"]
        track.scale_type = payload["scale_type"]

        secondary_ids = await self._validate_slugs(genre_slugs, mood_slugs, instrument_slugs)
        genres = await self.db.scalars(
            select(Genre).where(Genre.id.in_(secondary_ids["genre_ids"]))
        )
        moods = await self.db.scalars(select(Mood).where(Mood.id.in_(secondary_ids["mood_ids"])))
        instruments = await self.db.scalars(
            select(Instrument).where(Instrument.id.in_(secondary_ids["instrument_ids"]))
        )
        track.genres = list(genres)
        track.moods = list(moods)
        track.instruments = list(instruments)

        await self._set_track_tags(track, payload["tags"])

        await self.db.commit()
        await self.db.refresh(track)
        return track

    async def _set_track_tags(self, track: Track, tag_names: list[str]):
        normalized_tags = list({name.strip().lower() for name in tag_names if name.strip()})
        if not normalized_tags:
            track.tags = []
            return

        stmt = pg_insert(Tag).values([{"name": name} for name in normalized_tags])
        stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
        await self.db.execute(stmt)
        await self.db.commit()

        tags = await self.db.scalars(select(Tag).where(Tag.name.in_(normalized_tags)))
        track.tags = list(tags.all())

    async def _validate_slugs(
        self, genre_slugs: list[str], mood_slugs: list[str], instrument_slugs: list[str]
    ) -> dict[str, list[int]]:
        if not self.redis_client:
            raise RuntimeError("Redis client is required for slug validation")

        try:
            genre_ids = await resolve_slugs(self.redis_client, "genres", genre_slugs)
            mood_ids = await resolve_slugs(self.redis_client, "moods", mood_slugs)
            instrument_ids = await resolve_slugs(self.redis_client, "instruments", instrument_slugs)
        except ValueError as e:
            logger.error("Invalid slug: %s", e)
            raise SlugValidationError()

        return {"genre_ids": genre_ids, "mood_ids": mood_ids, "instrument_ids": instrument_ids}
