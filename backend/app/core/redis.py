import redis.asyncio as redis

from app.core.config import get_settings

app_settings = get_settings()
pool = redis.BlockingConnectionPool.from_url(
    app_settings.redis_url, decode_responses=True, max_connections=1, timeout=1
)
redis_client = redis.Redis(connection_pool=pool)


def get_redis() -> redis.Redis:
    return redis_client
