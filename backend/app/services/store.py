"""In-memory game store.

This module provides a simple in-memory store for games.
In production, this would be replaced with a proper database.
"""

from app.models.game import Game

# In-memory storage for games
_games: dict[str, Game] = {}
_invite_code_to_game_id: dict[str, str] = {}


def save_game(game: Game) -> None:
    """Save a game to the store."""
    _games[game.id] = game
    _invite_code_to_game_id[game.invite_code] = game.id


def get_game(game_id: str) -> Game | None:
    """Get a game by ID."""
    return _games.get(game_id)


def get_game_by_invite_code(invite_code: str) -> Game | None:
    """Get a game by invite code."""
    game_id = _invite_code_to_game_id.get(invite_code.upper())
    if game_id:
        return _games.get(game_id)
    return None


def clear_store() -> None:
    """Clear all games from the store. Useful for testing."""
    _games.clear()
    _invite_code_to_game_id.clear()
