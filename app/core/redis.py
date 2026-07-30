"""
Async Redis client singleton.
Used for: OTP caching, rate-limit counters, refresh token blacklist.
"""
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return (or lazily create) the global Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


# ── Convenience helpers ───────────────────────────────────────────────────────
async def redis_set(key: str, value: str, expire_seconds: int) -> None:
    r = await get_redis()
    await r.setex(key, expire_seconds, value)


async def redis_get(key: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(key)


async def redis_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def redis_increment(key: str, expire_seconds: int = 60) -> int:
    r = await get_redis()
    pipe = r.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, expire_seconds)
    results = await pipe.execute()
    return results[0]

async def redis_scan_keys(pattern: str) -> list[str]:
    """Returns all keys matching a pattern, e.g. 'refresh:{user_id}:*'."""
    r = await get_redis()
    return [key async for key in r.scan_iter(match=pattern)]


async def redis_delete_many(keys: list[str]) -> None:
    if not keys:
        return
    r = await get_redis()
    await r.delete(*keys)