from typing import List

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tracks.models import Genre, Instrument, Mood


async def sync_dictionary(redis: Redis, db: AsyncSession):
    result = await db.execute(select(Genre.id, Genre.slug))
    genres = result.all()
    result = await db.execute(select(Mood.id, Mood.slug))
    moods = result.all()
    result = await db.execute(select(Instrument.id, Instrument.slug))
    instruments = result.all()

    if genres:
        key = "dict:genres:slug_to_id"
        mapping = {g.slug: str(g.id) for g in genres}
        await redis.delete(key)
        await redis.hset(key, mapping=mapping)  # type: ignore[return-value]
    if moods:
        key = "dict:moods:slug_to_id"
        mapping = {m.slug: str(m.id) for m in moods}
        await redis.delete(key)
        await redis.hset(key, mapping=mapping)  # type: ignore[return-value]
    if instruments:
        key = "dict:instruments:slug_to_id"
        mapping = {i.slug: str(i.id) for i in instruments}
        await redis.delete(key)
        await redis.hset(key, mapping=mapping)  # type: ignore[return-value]


async def resolve_slugs(redis: Redis, table: str, slugs: List[str]) -> List[int]:
    key = f"dict:{table}:slug_to_id"

    pipe = redis.pipeline()
    for slug in slugs:
        pipe.hget(key, slug)
    results = await pipe.execute()

    ids: List[int] = []
    for slug, value in zip(slugs, results):
        if value is None:
            raise ValueError(f"Invalid {table} slug: {slug}")
        ids.append(int(value))
    return ids
