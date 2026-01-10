"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from app.models.api import (
    CreateGameRequest,
    GameCreatedResponse,
    GameStateResponse,
    JoinGameRequest,
    PlayerInfo,
)
from app.models.game import (
    Game,
    GameConfig,
    GamePhase,
    Player,
    Prompt,
    Round,
    Submission,
)
from app.models.websocket import (
    WSGameStarted,
    WSPlayerJoined,
    WSSubmitResponse,
)


class TestPlayer:
    """Tests for the Player model."""

    def test_player_creation_with_defaults(self) -> None:
        """Test creating a player with default values."""
        player = Player(nickname="Alice")

        assert player.nickname == "Alice"
        assert player.score == 0
        assert player.is_host is False
        assert player.is_connected is True
        assert player.word_tiles == []
        assert player.id is not None

    def test_player_creation_with_all_fields(self) -> None:
        """Test creating a player with all fields specified."""
        player = Player(
            id="player-123",
            nickname="Bob",
            score=3,
            is_host=True,
            is_connected=False,
            word_tiles=["hello", "world"],
        )

        assert player.id == "player-123"
        assert player.nickname == "Bob"
        assert player.score == 3
        assert player.is_host is True
        assert player.is_connected is False
        assert player.word_tiles == ["hello", "world"]

    def test_player_requires_nickname(self) -> None:
        """Test that nickname is required."""
        with pytest.raises(ValidationError):
            Player()


class TestPrompt:
    """Tests for the Prompt model."""

    def test_prompt_creation(self) -> None:
        """Test creating a prompt."""
        prompt = Prompt(text="What is the meaning of life?")

        assert prompt.text == "What is the meaning of life?"
        assert prompt.id is not None

    def test_prompt_with_custom_id(self) -> None:
        """Test creating a prompt with custom ID."""
        prompt = Prompt(id="prompt-1", text="Test prompt")

        assert prompt.id == "prompt-1"


class TestSubmission:
    """Tests for the Submission model."""

    def test_submission_creation(self) -> None:
        """Test creating a submission."""
        submission = Submission(
            player_id="player-1",
            tiles_used=["tile-1", "tile-2"],
            response_text="hello world",
        )

        assert submission.player_id == "player-1"
        assert submission.tiles_used == ["tile-1", "tile-2"]
        assert submission.response_text == "hello world"
        assert submission.submitted_at is not None


class TestRound:
    """Tests for the Round model."""

    def test_round_creation(self) -> None:
        """Test creating a round."""
        prompt = Prompt(text="Test prompt")
        round_ = Round(round_number=1, prompt=prompt, judge_id="judge-1")

        assert round_.round_number == 1
        assert round_.prompt.text == "Test prompt"
        assert round_.judge_id == "judge-1"
        assert round_.submissions == {}
        assert round_.winner_id is None


class TestGameConfig:
    """Tests for the GameConfig model."""

    def test_game_config_defaults(self) -> None:
        """Test game config default values."""
        config = GameConfig()

        assert config.tiles_per_player == 15
        assert config.points_to_win == 5
        assert config.submission_time_seconds == 90
        assert config.judging_time_seconds == 60
        assert config.min_players == 2
        assert config.max_players == 8

    def test_game_config_custom_values(self) -> None:
        """Test game config with custom values."""
        config = GameConfig(
            tiles_per_player=20,
            points_to_win=10,
            min_players=2,
            max_players=10,
        )

        assert config.tiles_per_player == 20
        assert config.points_to_win == 10
        assert config.min_players == 2
        assert config.max_players == 10


class TestGame:
    """Tests for the Game model."""

    def test_game_creation_with_defaults(self) -> None:
        """Test creating a game with default values."""
        game = Game(invite_code="ABC123")

        assert game.invite_code == "ABC123"
        assert game.phase == GamePhase.LOBBY
        assert game.players == {}
        assert game.current_round is None
        assert game.round_history == []
        assert game.config is not None
        assert game.word_pool == []
        assert game.prompts_pool == []
        assert game.id is not None

    def test_game_phase_enum(self) -> None:
        """Test that game phases are valid enum values."""
        assert GamePhase.LOBBY == "lobby"
        assert GamePhase.ROUND_SUBMISSION == "round_submission"
        assert GamePhase.ROUND_JUDGING == "round_judging"
        assert GamePhase.ROUND_RESULTS == "round_results"
        assert GamePhase.GAME_OVER == "game_over"


class TestApiModels:
    """Tests for API request/response models."""

    def test_create_game_request(self) -> None:
        """Test CreateGameRequest model."""
        request = CreateGameRequest(host_nickname="Host")
        assert request.host_nickname == "Host"
        assert request.config is None

    def test_create_game_request_with_config(self) -> None:
        """Test CreateGameRequest with custom config."""
        config = GameConfig(points_to_win=3)
        request = CreateGameRequest(host_nickname="Host", config=config)
        assert request.config is not None
        assert request.config.points_to_win == 3

    def test_join_game_request(self) -> None:
        """Test JoinGameRequest model."""
        request = JoinGameRequest(nickname="Player")
        assert request.nickname == "Player"

    def test_game_created_response(self) -> None:
        """Test GameCreatedResponse model."""
        player = Player(id="p1", nickname="Host", is_host=True)
        response = GameCreatedResponse(
            game_id="game-1",
            invite_code="ABC123",
            player_id="p1",
            player=player,
        )

        assert response.game_id == "game-1"
        assert response.invite_code == "ABC123"
        assert response.player.is_host is True

    def test_player_info(self) -> None:
        """Test PlayerInfo model (public player data)."""
        info = PlayerInfo(
            id="p1",
            nickname="Alice",
            score=2,
            is_host=True,
            is_connected=True,
        )

        assert info.id == "p1"
        assert info.nickname == "Alice"
        assert info.score == 2

    def test_game_state_response(self) -> None:
        """Test GameStateResponse model."""
        player_info = PlayerInfo(
            id="p1",
            nickname="Alice",
            score=0,
            is_host=True,
            is_connected=True,
        )
        response = GameStateResponse(
            game_id="game-1",
            invite_code="ABC123",
            phase=GamePhase.LOBBY,
            players=[player_info],
            current_round=None,
            config=GameConfig(),
            my_tiles=["word1", "word2"],
        )

        assert response.game_id == "game-1"
        assert response.phase == GamePhase.LOBBY
        assert len(response.players) == 1
        assert response.my_tiles == ["word1", "word2"]


class TestWebSocketModels:
    """Tests for WebSocket message models."""

    def test_ws_submit_response(self) -> None:
        """Test WSSubmitResponse model."""
        msg = WSSubmitResponse(tile_ids=["t1", "t2", "t3"])

        assert msg.type == "submit_response"
        assert msg.tile_ids == ["t1", "t2", "t3"]

    def test_ws_player_joined(self) -> None:
        """Test WSPlayerJoined model."""
        player = PlayerInfo(
            id="p1",
            nickname="Alice",
            score=0,
            is_host=False,
            is_connected=True,
        )
        msg = WSPlayerJoined(player=player, players=[player])

        assert msg.type == "player_joined"
        assert msg.player.nickname == "Alice"
        assert len(msg.players) == 1

    def test_ws_game_started(self) -> None:
        """Test WSGameStarted model."""
        prompt = Prompt(text="Test prompt")
        msg = WSGameStarted(
            round_number=1,
            prompt=prompt,
            judge_id="j1",
            your_tiles=["w1", "w2"],
        )

        assert msg.type == "game_started"
        assert msg.round_number == 1
        assert msg.judge_id == "j1"
        assert msg.your_tiles == ["w1", "w2"]
