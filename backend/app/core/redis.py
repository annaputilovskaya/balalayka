from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


async def check_redis() -> None:
    if not await get_redis().ping():
        raise RuntimeError("Redis is unavailable")
