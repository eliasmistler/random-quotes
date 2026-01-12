"""API request and response models."""

from pydantic import BaseModel

from app.models.game import GameConfig, GamePhase, Player, Prompt


class CreateGameRequest(BaseModel):
    """Request to create a new game."""

    host_nickname: str
    config: GameConfig | None = None


class JoinGameRequest(BaseModel):
    """Request to join an existing game."""

    nickname: str


class SubmitResponseRequest(BaseModel):
    """Request to submit a response for the current round."""

    tiles_used: list[str]


class SelectWinnerRequest(BaseModel):
    """Request to select the winner of the current round."""

    winner_player_id: str


class OverruleVoteRequest(BaseModel):
    """Request to cast an overrule vote."""

    vote_to_overrule: bool


class WinnerVoteRequest(BaseModel):
    """Request to vote for a new winner after overrule."""

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


class SubmissionInfo(BaseModel):
    """Submission information for judging phase."""

    player_id: str
    response_text: str


class RoundInfo(BaseModel):
    """Round information for the game state."""

    round_number: int
    prompt: Prompt
    judge_id: str | None  # None until all players submit
    submissions: list[SubmissionInfo]
    winner_id: str | None
    has_submitted: bool
    is_judge: bool
    # Overrule voting state
    judge_picked_self: bool = False
    overrule_votes: dict[str, bool] = {}
    can_overrule_vote: bool = False
    has_cast_overrule_vote: bool = False
    overruled: bool = False
    winner_votes: dict[str, str] = {}
    can_winner_vote: bool = False
    has_cast_winner_vote: bool = False


class GameStateResponse(BaseModel):
    """Full game state response for a specific player."""

    game_id: str
    invite_code: str
    phase: GamePhase
    players: list[PlayerInfo]
    current_round: RoundInfo | None
    config: GameConfig
    my_tiles: list[str]


class ActionResponse(BaseModel):
    """Generic response for game actions."""

    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    code: str
