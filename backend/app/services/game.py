"""Game logic services for Ransom Notes.

This module contains pure functions implementing the game logic.
"""

import random
import string

from app.models.content import GameContentConfig
from app.models.game import Game, GameConfig, GamePhase, Player, Prompt, Round, Submission


def generate_invite_code(length: int = 6) -> str:
    """Generate a random invite code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_player(nickname: str, is_host: bool = False) -> Player:
    """Create a new player."""
    return Player(nickname=nickname, is_host=is_host)


def create_game(host_nickname: str, config: GameConfig | None = None) -> tuple[Game, Player]:
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


def draw_tiles(word_pool: list[str], count: int) -> list[str]:
    """Draw random tiles from the word pool."""
    return random.sample(word_pool, min(count, len(word_pool)))


def distribute_tiles(game: Game, content: GameContentConfig) -> Game:
    """Distribute initial tiles to all players."""
    tiles_per_player = game.config.tiles_per_player
    updated_players = {}

    for player_id, player in game.players.items():
        tiles = draw_tiles(content.words, tiles_per_player)
        updated_players[player_id] = player.model_copy(update={"word_tiles": tiles})

    return game.model_copy(
        update={
            "players": updated_players,
            "word_pool": content.words.copy(),
        }
    )


def create_prompts_pool(content: GameContentConfig) -> list[Prompt]:
    """Create a pool of prompts from the content config."""
    return [Prompt(text=text) for text in content.prompts]


def select_next_prompt(game: Game) -> Prompt | None:
    """Select the next unused prompt from the pool."""
    available = [p for p in game.prompts_pool if p.id not in game.used_prompt_ids]
    if not available:
        return None
    return random.choice(available)


def get_player_ids_in_order(game: Game) -> list[str]:
    """Get player IDs in a consistent order for judge rotation."""
    return sorted(game.players.keys())


def select_judge(game: Game) -> str:
    """Select the judge for the next round based on rotation."""
    player_ids = get_player_ids_in_order(game)
    round_number = len(game.round_history) + 1
    judge_index = (round_number - 1) % len(player_ids)
    return player_ids[judge_index]


def start_game(game: Game, content: GameContentConfig) -> Game:
    """Start the game from the lobby phase.

    Raises ValueError if not enough players or not in lobby phase.
    """
    if game.phase != GamePhase.LOBBY:
        raise ValueError("Game is not in lobby phase")

    if len(game.players) < game.config.min_players:
        raise ValueError(f"Not enough players. Need at least {game.config.min_players}")

    game_with_tiles = distribute_tiles(game, content)
    game_with_prompts = game_with_tiles.model_copy(update={"prompts_pool": create_prompts_pool(content)})

    return start_new_round(game_with_prompts)


def start_new_round(game: Game) -> Game:
    """Start a new round of the game."""
    prompt = select_next_prompt(game)
    if prompt is None:
        return game.model_copy(update={"phase": GamePhase.GAME_OVER})

    judge_id = select_judge(game)
    new_round = Round(
        round_number=len(game.round_history) + 1,
        prompt=prompt,
        judge_id=judge_id,
    )

    return game.model_copy(
        update={
            "phase": GamePhase.ROUND_SUBMISSION,
            "current_round": new_round,
            "used_prompt_ids": [*game.used_prompt_ids, prompt.id],
        }
    )


def submit_response(game: Game, player_id: str, tiles_used: list[str]) -> Game:
    """Submit a player's response for the current round.

    Raises ValueError if player is the judge or already submitted.
    """
    if game.phase != GamePhase.ROUND_SUBMISSION:
        raise ValueError("Not in submission phase")

    if game.current_round is None:
        raise ValueError("No active round")

    if player_id == game.current_round.judge_id:
        raise ValueError("Judge cannot submit a response")

    if player_id in game.current_round.submissions:
        raise ValueError("Player has already submitted")

    player = game.players.get(player_id)
    if player is None:
        raise ValueError("Player not found")

    for tile in tiles_used:
        if tile not in player.word_tiles:
            raise ValueError(f"Player does not have tile: {tile}")

    submission = Submission(
        player_id=player_id,
        tiles_used=tiles_used,
        response_text=" ".join(tiles_used),
    )

    updated_submissions = {**game.current_round.submissions, player_id: submission}
    updated_round = game.current_round.model_copy(update={"submissions": updated_submissions})

    remaining_tiles = [t for t in player.word_tiles if t not in tiles_used]
    updated_player = player.model_copy(update={"word_tiles": remaining_tiles})
    updated_players = {**game.players, player_id: updated_player}

    return game.model_copy(
        update={
            "current_round": updated_round,
            "players": updated_players,
        }
    )


def all_submissions_in(game: Game) -> bool:
    """Check if all non-judge players have submitted."""
    if game.current_round is None:
        return False

    expected_submissions = len(game.players) - 1
    return len(game.current_round.submissions) >= expected_submissions


def advance_to_judging(game: Game) -> Game:
    """Advance the game to the judging phase."""
    if game.phase != GamePhase.ROUND_SUBMISSION:
        raise ValueError("Not in submission phase")

    return game.model_copy(update={"phase": GamePhase.ROUND_JUDGING})


def select_winner(game: Game, winner_id: str) -> Game:
    """Judge selects the winner of the current round.

    Raises ValueError if not in judging phase or winner didn't submit.
    """
    if game.phase != GamePhase.ROUND_JUDGING:
        raise ValueError("Not in judging phase")

    if game.current_round is None:
        raise ValueError("No active round")

    if winner_id not in game.current_round.submissions:
        raise ValueError("Winner must be a player who submitted")

    updated_round = game.current_round.model_copy(update={"winner_id": winner_id})

    winner = game.players[winner_id]
    updated_winner = winner.model_copy(update={"score": winner.score + 1})
    updated_players = {**game.players, winner_id: updated_winner}

    return game.model_copy(
        update={
            "phase": GamePhase.ROUND_RESULTS,
            "current_round": updated_round,
            "players": updated_players,
        }
    )


def check_game_over(game: Game) -> bool:
    """Check if any player has reached the winning score."""
    return any(p.score >= game.config.points_to_win for p in game.players.values())


def get_winner(game: Game) -> Player | None:
    """Get the player who won the game, if any."""
    for player in game.players.values():
        if player.score >= game.config.points_to_win:
            return player
    return None


def advance_round(game: Game, content: GameContentConfig) -> Game:
    """Advance from results to either the next round or game over."""
    if game.phase != GamePhase.ROUND_RESULTS:
        raise ValueError("Not in results phase")

    if game.current_round is None:
        raise ValueError("No current round")

    game_with_history = game.model_copy(update={"round_history": [*game.round_history, game.current_round]})

    if check_game_over(game_with_history):
        return game_with_history.model_copy(update={"phase": GamePhase.GAME_OVER})

    game_with_new_tiles = replenish_tiles(game_with_history, content)

    return start_new_round(game_with_new_tiles)


def replenish_tiles(game: Game, content: GameContentConfig) -> Game:
    """Replenish tiles for all players to reach the target count."""
    tiles_per_player = game.config.tiles_per_player
    updated_players = {}

    for player_id, player in game.players.items():
        tiles_needed = tiles_per_player - len(player.word_tiles)
        if tiles_needed > 0:
            new_tiles = draw_tiles(content.words, tiles_needed)
            all_tiles = player.word_tiles + new_tiles
            updated_players[player_id] = player.model_copy(update={"word_tiles": all_tiles})
        else:
            updated_players[player_id] = player

    return game.model_copy(update={"players": updated_players})
