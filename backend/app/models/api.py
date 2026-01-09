"""API request and response models."""

from pydantic import BaseModel

from app.models.game import GameConfig, GamePhase, Player, Round


class CreateGameRequest(BaseModel):
    """Request to create a new game."""

    host_nickname: str
    config: GameConfig | None = None


class JoinGameRequest(BaseModel):
    """Request to join an existing game."""

    nickname: str


class SubmitResponseRequest(BaseModel):
    """Request to submit a response for the current round."""

    tile_ids: list[str]


class SelectWinnerRequest(BaseModel):
    """Request to select the winner of the current round."""

    winner_player_id: str


class GameCreatedResponse(BaseModel):
    """Response after creating a new game."""

    game_id: str
    invite_code: str
    player_id: str
    player: Player


class GameJoinedResponse(BaseModel):
    """Response after joining a game."""

    game_id: str
    player_id: str
    player: Player


class PlayerInfo(BaseModel):
    """Public player information (without word tiles)."""

    id: str
    nickname: str
    score: int
    is_host: bool
    is_connected: bool


class GameStateResponse(BaseModel):
    """Full game state response for a specific player."""

    game_id: str
    invite_code: str
    phase: GamePhase
    players: list[PlayerInfo]
    current_round: Round | None
    config: GameConfig
    my_tiles: list[str]


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    code: str
