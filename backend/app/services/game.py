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


def is_nickname_taken(game: Game, nickname: str) -> bool:
    """Check if a nickname is already taken by a player in the game."""
    normalized = nickname.strip().lower()
    return any(p.nickname.strip().lower() == normalized for p in game.players.values())


def add_player_to_game(game: Game, nickname: str) -> tuple[Game, Player]:
    """Add a player to a game.

    Returns a new game with the player added and the new player.
    Raises ValueError if game is full, not in lobby phase, or nickname is taken.
    """
    if game.phase != GamePhase.LOBBY:
        raise ValueError("Cannot join game: game is not in lobby phase")

    if len(game.players) >= game.config.max_players:
        raise ValueError("Cannot join game: game is full")

    if is_nickname_taken(game, nickname):
        raise ValueError("Cannot join game: nickname is already taken")

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
    """Start a new round of the game.

    Judge is NOT selected here - all players submit first,
    then judge is selected when advancing to judging phase.
    """
    prompt = select_next_prompt(game)
    if prompt is None:
        return game.model_copy(update={"phase": GamePhase.GAME_OVER})

    new_round = Round(
        round_number=len(game.round_history) + 1,
        prompt=prompt,
        judge_id=None,  # Judge selected after all submit
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

    All players submit (including the future judge).
    Raises ValueError if already submitted.
    """
    if game.phase != GamePhase.ROUND_SUBMISSION:
        raise ValueError("Not in submission phase")

    if game.current_round is None:
        raise ValueError("No active round")

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
    """Check if all players have submitted."""
    if game.current_round is None:
        return False

    expected_submissions = len(game.players)
    return len(game.current_round.submissions) >= expected_submissions


def advance_to_judging(game: Game) -> Game:
    """Advance the game to the judging phase.

    Selects the judge now that all players have submitted.
    """
    if game.phase != GamePhase.ROUND_SUBMISSION:
        raise ValueError("Not in submission phase")

    if game.current_round is None:
        raise ValueError("No active round")

    judge_id = select_judge(game)
    updated_round = game.current_round.model_copy(update={"judge_id": judge_id})

    return game.model_copy(
        update={
            "phase": GamePhase.ROUND_JUDGING,
            "current_round": updated_round,
        }
    )


def select_winner(game: Game, winner_id: str) -> Game:
    """Judge selects the winner of the current round.

    Raises ValueError if not in judging phase or winner didn't submit.
    Tracks if the judge picked themselves (for potential overrule).
    If the winner reaches the winning score, skips straight to GAME_OVER.
    """
    if game.phase != GamePhase.ROUND_JUDGING:
        raise ValueError("Not in judging phase")

    if game.current_round is None:
        raise ValueError("No active round")

    if winner_id not in game.current_round.submissions:
        raise ValueError("Winner must be a player who submitted")

    judge_picked_self = winner_id == game.current_round.judge_id

    updated_round = game.current_round.model_copy(
        update={
            "winner_id": winner_id,
            "judge_picked_self": judge_picked_self,
        }
    )

    winner = game.players[winner_id]
    updated_winner = winner.model_copy(update={"score": winner.score + 1})
    updated_players = {**game.players, winner_id: updated_winner}

    updated_game = game.model_copy(
        update={
            "current_round": updated_round,
            "players": updated_players,
        }
    )

    # Check if game is over - skip round results and go straight to game over
    if check_game_over(updated_game):
        game_with_history = updated_game.model_copy(
            update={"round_history": [*updated_game.round_history, updated_round]}
        )
        return game_with_history.model_copy(update={"phase": GamePhase.GAME_OVER})

    return updated_game.model_copy(update={"phase": GamePhase.ROUND_RESULTS})


def check_game_over(game: Game) -> bool:
    """Check if any player has reached the winning score."""
    return any(p.score >= game.config.points_to_win for p in game.players.values())


def get_winner(game: Game) -> Player | None:
    """Get the player who won the game, if any."""
    for player in game.players.values():
        if player.score >= game.config.points_to_win:
            return player
    return None


def restart_game(game: Game) -> Game:
    """Restart the game with the same players.

    Resets all scores to 0, clears round history, and returns to lobby.
    Can only be called when game is over.
    """
    if game.phase != GamePhase.GAME_OVER:
        raise ValueError("Can only restart a finished game")

    # Reset all player scores to 0 and clear their tiles
    updated_players = {
        player_id: player.model_copy(update={"score": 0, "word_tiles": []})
        for player_id, player in game.players.items()
    }

    return game.model_copy(
        update={
            "phase": GamePhase.LOBBY,
            "players": updated_players,
            "current_round": None,
            "round_history": [],
        }
    )


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


def get_non_judge_player_ids(game: Game) -> list[str]:
    """Get list of player IDs excluding the judge."""
    if game.current_round is None or game.current_round.judge_id is None:
        return list(game.players.keys())
    return [pid for pid in game.players.keys() if pid != game.current_round.judge_id]


def can_cast_overrule_vote(game: Game) -> bool:
    """Check if overrule voting is currently possible."""
    if game.phase != GamePhase.ROUND_RESULTS:
        return False
    if game.current_round is None:
        return False
    if not game.current_round.judge_picked_self:
        return False
    if len(game.players) < 3:
        return False
    if game.current_round.overruled:
        return False
    return True


def can_cast_winner_vote(game: Game) -> bool:
    """Check if winner voting is currently possible."""
    if game.phase != GamePhase.ROUND_RESULTS:
        return False
    if game.current_round is None:
        return False
    if not game.current_round.overruled:
        return False
    if game.current_round.winner_id is not None:
        return False
    return True


def cast_overrule_vote(game: Game, player_id: str, vote_to_overrule: bool) -> Game:
    """Cast an overrule vote during the results phase.

    Only non-judge players can vote, and only when:
    - In ROUND_RESULTS phase
    - Judge picked themselves
    - There are 3+ players

    Returns updated game. If unanimous overrule, reverts the winner's point.
    """
    if game.phase != GamePhase.ROUND_RESULTS:
        raise ValueError("Not in results phase")

    if game.current_round is None:
        raise ValueError("No active round")

    if not game.current_round.judge_picked_self:
        raise ValueError("Overrule vote only available when judge picked themselves")

    if len(game.players) < 3:
        raise ValueError("Overrule vote requires 3+ players")

    if player_id == game.current_round.judge_id:
        raise ValueError("Judge cannot vote on overrule")

    if player_id not in game.players:
        raise ValueError("Player not found")

    if player_id in game.current_round.overrule_votes:
        raise ValueError("Player has already voted")

    updated_votes = {**game.current_round.overrule_votes, player_id: vote_to_overrule}
    updated_round = game.current_round.model_copy(update={"overrule_votes": updated_votes})
    updated_game = game.model_copy(update={"current_round": updated_round})

    non_judge_players = get_non_judge_player_ids(game)

    if len(updated_votes) == len(non_judge_players):
        if all(updated_votes.values()):
            judge_id = game.current_round.judge_id
            judge = updated_game.players[judge_id]
            updated_judge = judge.model_copy(update={"score": judge.score - 1})
            updated_players = {**updated_game.players, judge_id: updated_judge}

            updated_round = updated_round.model_copy(
                update={
                    "overruled": True,
                    "winner_id": None,
                }
            )
            updated_game = updated_game.model_copy(
                update={
                    "current_round": updated_round,
                    "players": updated_players,
                }
            )

    return updated_game


def cast_winner_vote(game: Game, voter_id: str, winner_id: str) -> Game:
    """Cast a vote for the new winner after overrule succeeded.

    Only non-judge players can vote for a new winner.
    Winner must be a player who submitted (not the judge).
    """
    if game.phase != GamePhase.ROUND_RESULTS:
        raise ValueError("Not in results phase")

    if game.current_round is None:
        raise ValueError("No active round")

    if not game.current_round.overruled:
        raise ValueError("Winner voting only available after successful overrule")

    if voter_id == game.current_round.judge_id:
        raise ValueError("Judge cannot vote for winner")

    if voter_id not in game.players:
        raise ValueError("Voter not found")

    if voter_id in game.current_round.winner_votes:
        raise ValueError("Player has already voted for winner")

    if winner_id not in game.current_round.submissions:
        raise ValueError("Winner must be a player who submitted")

    if winner_id == game.current_round.judge_id:
        raise ValueError("Cannot vote for the judge")

    updated_votes = {**game.current_round.winner_votes, voter_id: winner_id}
    updated_round = game.current_round.model_copy(update={"winner_votes": updated_votes})
    updated_game = game.model_copy(update={"current_round": updated_round})

    non_judge_players = get_non_judge_player_ids(game)

    if len(updated_votes) == len(non_judge_players):
        updated_game = determine_voted_winner(updated_game)

    return updated_game


def determine_voted_winner(game: Game) -> Game:
    """Determine the winner based on plurality voting.

    In case of tie, the player who submitted first wins.
    """
    if game.current_round is None:
        raise ValueError("No active round")

    winner_votes = game.current_round.winner_votes

    vote_counts: dict[str, int] = {}
    for voted_winner in winner_votes.values():
        vote_counts[voted_winner] = vote_counts.get(voted_winner, 0) + 1

    max_votes = max(vote_counts.values())

    top_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

    if len(top_candidates) > 1:
        submissions = game.current_round.submissions
        winner_id = min(top_candidates, key=lambda pid: submissions[pid].submitted_at)
    else:
        winner_id = top_candidates[0]

    winner = game.players[winner_id]
    updated_winner = winner.model_copy(update={"score": winner.score + 1})
    updated_players = {**game.players, winner_id: updated_winner}

    updated_round = game.current_round.model_copy(update={"winner_id": winner_id})

    return game.model_copy(
        update={
            "current_round": updated_round,
            "players": updated_players,
        }
    )
