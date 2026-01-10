"""API routes for the Ransom Notes application."""

from fastapi import APIRouter, HTTPException

from app.models.api import (
    CreateGameRequest,
    ErrorResponse,
    GameCreatedResponse,
    GameJoinedResponse,
    GameStateResponse,
    JoinGameRequest,
    PlayerInfo,
)
from app.models.common import HealthResponse
from app.services.game import add_player_to_game, create_game
from app.services.store import get_game, get_game_by_invite_code, save_game

router = APIRouter()


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
        current_round=game.current_round,
        config=game.config,
        my_tiles=player.word_tiles,
    )
