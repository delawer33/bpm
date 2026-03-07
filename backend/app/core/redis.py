import redis.asyncio as redis

from app.core.config import get_settings

app_settings = get_settings()
redis_client = redis.Redis.from_url(app_settings.redis_url, decode_responses=True)


async def get_redis():
    return redis_client
