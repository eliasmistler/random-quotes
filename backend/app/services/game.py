"""Game logic services for Ransom Notes.

This module contains pure functions implementing the game logic.
"""

import random
import string

from app.models.game import Game, GameConfig, GamePhase, Player


def generate_invite_code(length: int = 6) -> str:
    """Generate a random invite code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_player(nickname: str, is_host: bool = False) -> Player:
    """Create a new player."""
    return Player(nickname=nickname, is_host=is_host)


def create_game(
    host_nickname: str, config: GameConfig | None = None
) -> tuple[Game, Player]:
    """Create a new game with a host player.

    Returns a tuple of (game, host_player).
    """
    host = create_player(nickname=host_nickname, is_host=True)
    game_config = config or GameConfig()
    game = Game(
        invite_code=generate_invite_code(),
        phase=GamePhase.LOBBY,
        players={host.id: host},
        config=game_config,
    )
    return game, host


def add_player_to_game(game: Game, nickname: str) -> tuple[Game, Player]:
    """Add a player to a game.

    Returns a new game with the player added and the new player.
    Raises ValueError if game is full or not in lobby phase.
    """
    if game.phase != GamePhase.LOBBY:
        raise ValueError("Cannot join game: game is not in lobby phase")

    if len(game.players) >= game.config.max_players:
        raise ValueError("Cannot join game: game is full")

    new_player = create_player(nickname=nickname, is_host=False)
    updated_players = {**game.players, new_player.id: new_player}
    updated_game = game.model_copy(update={"players": updated_players})
    return updated_game, new_player


def get_player_from_game(game: Game, player_id: str) -> Player | None:
    """Get a player from a game by ID."""
    return game.players.get(player_id)
