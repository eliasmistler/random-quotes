"""Core domain models for the Ransom Notes game."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    """Game state phases."""

    LOBBY = "lobby"
    ROUND_SUBMISSION = "round_submission"
    ROUND_JUDGING = "round_judging"
    ROUND_RESULTS = "round_results"
    GAME_OVER = "game_over"


class Player(BaseModel):
    """Represents a player in the game."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    nickname: str
    score: int = 0
    is_host: bool = False
    is_connected: bool = True
    word_tiles: list[str] = Field(default_factory=list)


class Prompt(BaseModel):
    """A game prompt/question."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str


class Submission(BaseModel):
    """A player's submission for a round."""

    player_id: str
    tiles_used: list[str]
    response_text: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class Round(BaseModel):
    """Represents a single game round."""

    round_number: int
    prompt: Prompt
    judge_id: str
    submissions: dict[str, Submission] = Field(default_factory=dict)
    winner_id: str | None = None


class GameConfig(BaseModel):
    """Game configuration settings."""

    tiles_per_player: int = 15
    points_to_win: int = 5
    submission_time_seconds: int = 90
    judging_time_seconds: int = 60
    min_players: int = 2
    max_players: int = 8


class Game(BaseModel):
    """Main game state container."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    invite_code: str
    phase: GamePhase = GamePhase.LOBBY
    players: dict[str, Player] = Field(default_factory=dict)
    current_round: Round | None = None
    round_history: list[Round] = Field(default_factory=list)
    config: GameConfig = Field(default_factory=GameConfig)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    word_pool: list[str] = Field(default_factory=list)
    prompts_pool: list[Prompt] = Field(default_factory=list)
    used_prompt_ids: list[str] = Field(default_factory=list)
