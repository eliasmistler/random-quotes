"""Redis-backed game store.

This module provides persistent storage for games using Redis.
"""

import logging

from redis.asyncio import Redis

from app.config import get_settings
from app.models.game import Game
from app.services.redis_client import get_redis

log = logging.getLogger(__name__)

# Key prefixes for Redis
GAME_KEY_PREFIX = "game:"
INVITE_KEY_PREFIX = "invite:"


def _game_key(game_id: str) -> str:
    """Generate Redis key for a game."""
    return f"{GAME_KEY_PREFIX}{game_id}"


def _invite_key(invite_code: str) -> str:
    """Generate Redis key for an invite code mapping."""
    return f"{INVITE_KEY_PREFIX}{invite_code.upper()}"


async def save_game(game: Game) -> None:
    """Save a game to Redis.

    Stores the game JSON and creates invite code mapping atomically.
    """
    settings = get_settings()
    redis: Redis = await get_redis()

    game_key = _game_key(game.id)
    invite_key = _invite_key(game.invite_code)

    # Use pipeline for atomic operations
    async with redis.pipeline() as pipe:
        # Store game as JSON string
        pipe.set(game_key, game.model_dump_json())
        # Store invite code -> game ID mapping
        pipe.set(invite_key, game.id)

        # Apply TTL if configured
        if settings.game_ttl_seconds:
            pipe.expire(game_key, settings.game_ttl_seconds)
            pipe.expire(invite_key, settings.game_ttl_seconds)

        await pipe.execute()


async def get_game(game_id: str) -> Game | None:
    """Get a game by ID from Redis."""
    redis: Redis = await get_redis()

    game_json = await redis.get(_game_key(game_id))
    if game_json is None:
        return None

    return Game.model_validate_json(game_json)


async def get_game_by_invite_code(invite_code: str) -> Game | None:
    """Get a game by invite code from Redis."""
    redis: Redis = await get_redis()

    # Look up game ID from invite code
    game_id = await redis.get(_invite_key(invite_code))
    if game_id is None:
        return None

    return await get_game(game_id)


async def delete_game(game_id: str) -> bool:
    """Delete a game from Redis.

    Returns True if the game was deleted, False if it didn't exist.
    """
    redis: Redis = await get_redis()

    # First get the game to find its invite code
    game = await get_game(game_id)
    if game is None:
        return False

    async with redis.pipeline() as pipe:
        pipe.delete(_game_key(game_id))
        pipe.delete(_invite_key(game.invite_code))
        await pipe.execute()

    return True


async def clear_store() -> None:
    """Clear all games from the store. Useful for testing.

    WARNING: This deletes ALL keys matching game/invite patterns.
    """
    redis: Redis = await get_redis()

    # Delete all game keys
    async for key in redis.scan_iter(match=f"{GAME_KEY_PREFIX}*"):
        await redis.delete(key)

    # Delete all invite keys
    async for key in redis.scan_iter(match=f"{INVITE_KEY_PREFIX}*"):
        await redis.delete(key)
