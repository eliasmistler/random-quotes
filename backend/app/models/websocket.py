"""WebSocket message models for real-time game communication."""

from typing import Literal

from pydantic import BaseModel

from app.models.api import PlayerInfo
from app.models.game import GamePhase, Prompt

# =============================================================================
# Client -> Server Messages
# =============================================================================


class WSStartGame(BaseModel):
    """Client message to start the game (host only)."""

    type: Literal["start_game"] = "start_game"


class WSSubmitResponse(BaseModel):
    """Client message to submit a response."""

    type: Literal["submit_response"] = "submit_response"
    tile_ids: list[str]


class WSSelectWinner(BaseModel):
    """Client message to select the round winner (judge only)."""

    type: Literal["select_winner"] = "select_winner"
    winner_player_id: str


class WSPing(BaseModel):
    """Client keep-alive message."""

    type: Literal["ping"] = "ping"


# =============================================================================
# Server -> Client Messages
# =============================================================================


class WSPlayerJoined(BaseModel):
    """Server message when a player joins."""

    type: Literal["player_joined"] = "player_joined"
    player: PlayerInfo
    players: list[PlayerInfo]


class WSPlayerLeft(BaseModel):
    """Server message when a player leaves."""

    type: Literal["player_left"] = "player_left"
    player_id: str
    players: list[PlayerInfo]


class WSGameStarted(BaseModel):
    """Server message when the game starts."""

    type: Literal["game_started"] = "game_started"
    round_number: int
    prompt: Prompt
    judge_id: str
    your_tiles: list[str]


class WSRoundStarted(BaseModel):
    """Server message when a new round starts."""

    type: Literal["round_started"] = "round_started"
    round_number: int
    prompt: Prompt
    judge_id: str
    your_tiles: list[str]


class WSSubmissionReceived(BaseModel):
    """Server message when a submission is received."""

    type: Literal["submission_received"] = "submission_received"
    player_id: str
    submissions_count: int
    total_expected: int


class AnonymousSubmission(BaseModel):
    """A submission without player identification (for judging)."""

    submission_id: str
    response_text: str


class WSJudgingPhase(BaseModel):
    """Server message when judging phase begins."""

    type: Literal["judging_phase"] = "judging_phase"
    submissions: list[AnonymousSubmission]


class WSRoundResults(BaseModel):
    """Server message with round results."""

    type: Literal["round_results"] = "round_results"
    winner_id: str
    winner_nickname: str
    winning_response: str
    scores: dict[str, int]


class WSGameOver(BaseModel):
    """Server message when the game ends."""

    type: Literal["game_over"] = "game_over"
    winner_id: str
    winner_nickname: str
    final_scores: dict[str, int]


class WSTilesUpdated(BaseModel):
    """Server message when a player's tiles change."""

    type: Literal["tiles_updated"] = "tiles_updated"
    tiles: list[str]


class WSPhaseChange(BaseModel):
    """Server message when game phase changes."""

    type: Literal["phase_change"] = "phase_change"
    phase: GamePhase
    time_remaining: int | None = None


class WSError(BaseModel):
    """Server error message."""

    type: Literal["error"] = "error"
    message: str
    code: str


class WSPong(BaseModel):
    """Server keep-alive response."""

    type: Literal["pong"] = "pong"
