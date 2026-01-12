"""API routes for the Ransom Notes application."""

import logging

from fastapi import APIRouter, HTTPException

from app.models.api import (
    ActionResponse,
    CreateGameRequest,
    ErrorResponse,
    GameCreatedResponse,
    GameJoinedResponse,
    GameStateResponse,
    JoinGameRequest,
    OverruleVoteRequest,
    PlayerInfo,
    RoundInfo,
    SelectWinnerRequest,
    SubmissionInfo,
    SubmitResponseRequest,
    WinnerVoteRequest,
)
from app.models.common import HealthResponse
from app.models.content import load_game_content
from app.models.game import GamePhase
from app.services.game import (
    add_player_to_game,
    advance_round,
    advance_to_judging,
    all_submissions_in,
    can_cast_overrule_vote,
    can_cast_winner_vote,
    cast_overrule_vote,
    cast_winner_vote,
    create_game,
    get_non_judge_player_ids,
    select_winner,
    start_game,
    submit_response,
)
from app.services.store import get_game, get_game_by_invite_code, save_game

router = APIRouter()
logger = logging.getLogger(__name__)

_game_content = load_game_content()


def _build_round_info(game, player_id: str) -> RoundInfo | None:
    """Build round info for the current player."""
    if game.current_round is None:
        return None

    show_submissions = game.phase in (
        GamePhase.ROUND_JUDGING,
        GamePhase.ROUND_RESULTS,
    )

    submissions = []
    if show_submissions:
        submissions = [
            SubmissionInfo(player_id=s.player_id, response_text=s.response_text)
            for s in game.current_round.submissions.values()
        ]

    can_overrule = (
        can_cast_overrule_vote(game)
        and player_id != game.current_round.judge_id
        and player_id not in game.current_round.overrule_votes
    )

    can_winner = (
        can_cast_winner_vote(game)
        and player_id != game.current_round.judge_id
        and player_id not in game.current_round.winner_votes
    )

    return RoundInfo(
        round_number=game.current_round.round_number,
        prompt=game.current_round.prompt,
        judge_id=game.current_round.judge_id,
        submissions=submissions,
        winner_id=game.current_round.winner_id,
        has_submitted=player_id in game.current_round.submissions,
        is_judge=player_id == game.current_round.judge_id,
        judge_picked_self=game.current_round.judge_picked_self,
        overrule_votes=game.current_round.overrule_votes,
        can_overrule_vote=can_overrule,
        has_cast_overrule_vote=player_id in game.current_round.overrule_votes,
        overruled=game.current_round.overruled,
        winner_votes=game.current_round.winner_votes,
        can_winner_vote=can_winner,
        has_cast_winner_vote=player_id in game.current_round.winner_votes,
    )


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


@router.post(
    "/games",
    response_model=GameCreatedResponse,
    responses={400: {"model": ErrorResponse}},
)
def create_new_game(request: CreateGameRequest) -> GameCreatedResponse:
    """Create a new game and become the host."""
    game, host = create_game(
        host_nickname=request.host_nickname,
        config=request.config,
    )
    save_game(game)
    return GameCreatedResponse(
        game_id=game.id,
        invite_code=game.invite_code,
        player_id=host.id,
        player=host,
    )


@router.post(
    "/games/join/{invite_code}",
    response_model=GameJoinedResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def join_game(invite_code: str, request: JoinGameRequest) -> GameJoinedResponse:
    """Join an existing game using an invite code."""
    game = get_game_by_invite_code(invite_code)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    try:
        updated_game, new_player = add_player_to_game(game, request.nickname)
        save_game(updated_game)
        return GameJoinedResponse(
            game_id=updated_game.id,
            player_id=new_player.id,
            player=new_player,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_JOIN"},
        ) from e


@router.get(
    "/games/{game_id}",
    response_model=GameStateResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_game_state(game_id: str, player_id: str) -> GameStateResponse:
    """Get the current state of a game for a specific player."""
    game = get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    player = game.players.get(player_id)
    if not player:
        raise HTTPException(
            status_code=404,
            detail={"error": "Player not found in game", "code": "PLAYER_NOT_FOUND"},
        )

    players_info = [
        PlayerInfo(
            id=p.id,
            nickname=p.nickname,
            score=p.score,
            is_host=p.is_host,
            is_connected=p.is_connected,
        )
        for p in game.players.values()
    ]

    return GameStateResponse(
        game_id=game.id,
        invite_code=game.invite_code,
        phase=game.phase,
        players=players_info,
        current_round=_build_round_info(game, player_id),
        config=game.config,
        my_tiles=player.word_tiles,
    )


@router.post(
    "/games/{game_id}/start",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def start_game_endpoint(game_id: str, player_id: str) -> ActionResponse:
    """Start the game. Only the host can start the game."""
    logger.info("Start game request: game_id=%s, player_id=%s", game_id, player_id)

    game = get_game(game_id)
    if not game:
        logger.warning("Start game failed: game not found (game_id=%s)", game_id)
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    logger.info(
        "Game state: phase=%s, players=%d, min_players=%d",
        game.phase,
        len(game.players),
        game.config.min_players,
    )

    player = game.players.get(player_id)
    if not player:
        logger.warning(
            "Start game failed: player not found (game_id=%s, player_id=%s)",
            game_id,
            player_id,
        )
        raise HTTPException(
            status_code=404,
            detail={"error": "Player not found", "code": "PLAYER_NOT_FOUND"},
        )

    if not player.is_host:
        logger.warning("Start game failed: player is not host (player=%s)", player.nickname)
        raise HTTPException(
            status_code=403,
            detail={"error": "Only the host can start the game", "code": "NOT_HOST"},
        )

    try:
        updated_game = start_game(game, _game_content)
        save_game(updated_game)
        logger.info("Game started successfully: game_id=%s", game_id)
        return ActionResponse(success=True, message="Game started")
    except ValueError as e:
        logger.warning("Start game failed: %s (game_id=%s)", str(e), game_id)
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_START"},
        ) from e
    except Exception as e:
        logger.exception("Unexpected error starting game: game_id=%s", game_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Internal server error: {str(e)}",
                "code": "SERVER_ERROR",
            },
        ) from e


@router.post(
    "/games/{game_id}/submit",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def submit_response_endpoint(game_id: str, player_id: str, request: SubmitResponseRequest) -> ActionResponse:
    """Submit a response for the current round."""
    game = get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    try:
        updated_game = submit_response(game, player_id, request.tiles_used)

        if all_submissions_in(updated_game):
            updated_game = advance_to_judging(updated_game)

        save_game(updated_game)
        return ActionResponse(success=True, message="Response submitted")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_SUBMIT"},
        ) from e


@router.post(
    "/games/{game_id}/judge",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def select_winner_endpoint(game_id: str, player_id: str, request: SelectWinnerRequest) -> ActionResponse:
    """Judge selects the winner of the current round."""
    game = get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    if game.current_round is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "No active round", "code": "NO_ROUND"},
        )

    if player_id != game.current_round.judge_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "Only the judge can select a winner", "code": "NOT_JUDGE"},
        )

    try:
        updated_game = select_winner(game, request.winner_player_id)
        save_game(updated_game)
        return ActionResponse(success=True, message="Winner selected")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_JUDGE"},
        ) from e


@router.post(
    "/games/{game_id}/advance",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def advance_round_endpoint(game_id: str, player_id: str) -> ActionResponse:
    """Advance to the next round after results are shown."""
    game = get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    player = game.players.get(player_id)
    if not player:
        raise HTTPException(
            status_code=404,
            detail={"error": "Player not found", "code": "PLAYER_NOT_FOUND"},
        )

    if not player.is_host:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the host can advance the round",
                "code": "NOT_HOST",
            },
        )

    try:
        updated_game = advance_round(game, _game_content)
        save_game(updated_game)

        if updated_game.phase == GamePhase.GAME_OVER:
            return ActionResponse(success=True, message="Game over")
        return ActionResponse(success=True, message="Next round started")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_ADVANCE"},
        ) from e


@router.post(
    "/games/{game_id}/overrule",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def cast_overrule_vote_endpoint(game_id: str, player_id: str, request: OverruleVoteRequest) -> ActionResponse:
    """Cast a vote to overrule the judge's self-pick."""
    game = get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    try:
        updated_game = cast_overrule_vote(game, player_id, request.vote_to_overrule)
        save_game(updated_game)

        if updated_game.current_round and updated_game.current_round.overruled:
            return ActionResponse(success=True, message="Overrule succeeded - vote for new winner")

        non_judge_count = len(get_non_judge_player_ids(game))
        votes_cast = len(updated_game.current_round.overrule_votes) if updated_game.current_round else 0

        if votes_cast >= non_judge_count:
            return ActionResponse(success=True, message="Overrule vote failed - original winner stands")

        return ActionResponse(success=True, message="Overrule vote cast")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_VOTE"},
        ) from e


@router.post(
    "/games/{game_id}/vote-winner",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def cast_winner_vote_endpoint(game_id: str, player_id: str, request: WinnerVoteRequest) -> ActionResponse:
    """Cast a vote for the new winner after successful overrule."""
    game = get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "code": "GAME_NOT_FOUND"},
        )

    try:
        updated_game = cast_winner_vote(game, player_id, request.winner_player_id)
        save_game(updated_game)

        if updated_game.current_round and updated_game.current_round.winner_id is not None:
            winner = updated_game.players[updated_game.current_round.winner_id]
            return ActionResponse(success=True, message=f"New winner: {winner.nickname}")

        return ActionResponse(success=True, message="Winner vote cast")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "CANNOT_VOTE"},
        ) from e
