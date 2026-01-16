"""Redis client connection management."""

import logging

from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings

log = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create the Redis connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            retry_on_timeout=settings.redis_retry_on_timeout,
            decode_responses=True,
        )
        log.info("Redis connection pool created")
    return _pool


async def get_redis() -> Redis:
    """Get a Redis client instance from the pool."""
    pool = await get_redis_pool()
    return Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
        log.info("Redis connection pool closed")


async def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception as e:
        log.warning(f"Redis health check failed: {e}")
        return False
