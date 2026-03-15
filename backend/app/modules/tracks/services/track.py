import logging
import uuid
import base64
import json

from datetime import datetime
from redis.asyncio import Redis
from sqlalchemy import select, tuple_
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
from app.modules.tracks.models.track import Track, TrackStatus, TrackVisibility
from app.modules.tracks.models.track_file import TrackFile, TrackFileStatus, TrackFileType
from app.modules.tracks.schemas import STrackListFilters, STrackUpload

REQUIRED_FILE_TYPES = (
    TrackFileType.PREVIEW,
    TrackFileType.MAIN,
    TrackFileType.STEMS,
    TrackFileType.IMAGE,
)

logger = logging.getLogger("app_logger")



def encode_track_cursor(created_at: datetime, track_id: uuid.UUID) -> str:
    payload = {
        "created_at": created_at.isoformat(),
        "id": str(track_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_track_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        payload = json.loads(raw.decode())
        created_at = datetime.fromisoformat(payload["created_at"])
        track_id = uuid.UUID(payload["id"])
        return created_at, track_id
    except (ValueError, KeyError, TypeError):
        return None

class TrackService:
    def __init__(self, db: AsyncSession, redis_client: Redis | None = None) -> None:
        self.db = db
        self.redis_client = redis_client

    async def create_draft(self, user_id: uuid.UUID) -> Track:
        track = Track(user_id=user_id)
        self.db.add(track)
        await self.db.flush()
        return track

    async def get_tracks_for_owner(
        self, user_id: uuid.UUID, filters: STrackListFilters
    ) -> tuple[list[Track], str | None]:
        stmt = select(Track).where(Track.user_id == user_id)

        if filters.status:
            stmt = stmt.where(Track.status.in_([s.value for s in filters.status]))
        if filters.bpm_min is not None:
            stmt = stmt.where(Track.bpm >= filters.bpm_min)
        if filters.bpm_max is not None:
            stmt = stmt.where(Track.bpm <= filters.bpm_max)
        if filters.root_note:
            stmt = stmt.where(Track.root_note.in_(filters.root_note))
        if filters.scale_type:
            stmt = stmt.where(Track.scale_type.in_(filters.scale_type))
        if filters.visibility:
            stmt = stmt.where(
                Track.visibility.in_([v.value for v in filters.visibility])
            )

        if filters.cursor:
            decoded = decode_track_cursor(filters.cursor)
            if decoded:
                c_created_at, c_id = decoded
                stmt = stmt.where(
                    tuple_(Track.created_at, Track.id) < (c_created_at, c_id)
                )

        stmt = stmt.order_by(Track.created_at.desc(), Track.id.desc())
        stmt = stmt.limit(filters.limit + 1)

        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor = None
        if len(rows) > filters.limit:
            last = rows[filters.limit - 1]
            next_cursor = encode_track_cursor(last.created_at, last.id)
            rows = rows[: filters.limit]

        return rows, next_cursor

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

    async def update_track_status_for_files(self, track_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(TrackFile).where(
                TrackFile.track_id == track_id,
                TrackFile.file_type.in_([t.value for t in REQUIRED_FILE_TYPES]),
            )
        )
        files = list(result.scalars().all())
        by_type = {f.file_type: f for f in files}
        if len(by_type) < len(REQUIRED_FILE_TYPES):
            return
        any_failed = any(f.status == TrackFileStatus.FAILED for f in files)
        all_ready = all(f.status == TrackFileStatus.READY for f in files)
        track = await self.db.get(Track, track_id)
        if not track:
            return
        if any_failed:
            track.status = TrackStatus.FAILED
        elif all_ready:
            track.status = TrackStatus.READY
        else:
            track.status = TrackStatus.PROCESSING
