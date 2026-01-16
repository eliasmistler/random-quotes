"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_status(self, client: AsyncClient) -> None:
        """Test that health check endpoint returns healthy status."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestCreateGameEndpoint:
    """Tests for the POST /games endpoint."""

    @pytest.mark.asyncio
    async def test_create_game_returns_game_info(self, client: AsyncClient) -> None:
        """Test that creating a game returns all required fields."""
        response = await client.post("/api/games", json={"host_nickname": "TestHost"})

        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert "invite_code" in data
        assert "player_id" in data
        assert "player" in data
        assert len(data["invite_code"]) == 6
        assert data["player"]["nickname"] == "TestHost"
        assert data["player"]["is_host"] is True
        assert data["player"]["score"] == 0

    @pytest.mark.asyncio
    async def test_create_game_generates_unique_ids(self, client: AsyncClient) -> None:
        """Test that each game gets unique IDs."""
        response1 = await client.post("/api/games", json={"host_nickname": "Host1"})
        response2 = await client.post("/api/games", json={"host_nickname": "Host2"})

        data1 = response1.json()
        data2 = response2.json()

        assert data1["game_id"] != data2["game_id"]
        assert data1["player_id"] != data2["player_id"]

    @pytest.mark.asyncio
    async def test_create_game_with_custom_config(self, client: AsyncClient) -> None:
        """Test creating a game with custom configuration."""
        custom_config = {
            "tiles_per_player": 12,
            "points_to_win": 5,
            "max_players": 6,
        }
        response = await client.post(
            "/api/games",
            json={"host_nickname": "TestHost", "config": custom_config},
        )

        assert response.status_code == 200
        game_id = response.json()["game_id"]
        player_id = response.json()["player_id"]

        state_resp = await client.get(f"/api/games/{game_id}?player_id={player_id}")
        state = state_resp.json()
        assert state["config"]["tiles_per_player"] == 12
        assert state["config"]["points_to_win"] == 5
        assert state["config"]["max_players"] == 6


class TestJoinGameEndpoint:
    """Tests for the POST /games/join/{invite_code} endpoint."""

    @pytest.mark.asyncio
    async def test_join_game_success(self, client: AsyncClient) -> None:
        """Test successfully joining a game."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        invite_code = create_resp.json()["invite_code"]

        join_resp = await client.post(
            f"/api/games/join/{invite_code}",
            json={"nickname": "Player2"},
        )

        assert join_resp.status_code == 200
        data = join_resp.json()
        assert "game_id" in data
        assert "player_id" in data
        assert data["player"]["nickname"] == "Player2"
        assert data["player"]["is_host"] is False

    @pytest.mark.asyncio
    async def test_join_game_case_insensitive_invite_code(self, client: AsyncClient) -> None:
        """Test that invite codes are case insensitive."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        invite_code = create_resp.json()["invite_code"]

        join_resp = await client.post(
            f"/api/games/join/{invite_code.lower()}",
            json={"nickname": "Player2"},
        )

        assert join_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_join_nonexistent_game_returns_404(self, client: AsyncClient) -> None:
        """Test that joining a non-existent game returns 404."""
        response = await client.post(
            "/api/games/join/INVALID",
            json={"nickname": "Player"},
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "GAME_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_join_game_duplicate_nickname_rejected(self, client: AsyncClient) -> None:
        """Test that joining with a nickname already taken returns 400."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Player1"})
        invite_code = create_resp.json()["invite_code"]

        # Try to join with the same nickname as the host
        join_resp = await client.post(
            f"/api/games/join/{invite_code}",
            json={"nickname": "Player1"},
        )

        assert join_resp.status_code == 400
        assert "nickname is already taken" in join_resp.json()["detail"]["error"].lower()

    @pytest.mark.asyncio
    async def test_join_game_duplicate_nickname_case_insensitive(self, client: AsyncClient) -> None:
        """Test that nickname uniqueness check is case-insensitive."""
        create_resp = await client.post("/api/games", json={"host_nickname": "TestPlayer"})
        invite_code = create_resp.json()["invite_code"]

        # Try to join with different casing
        join_resp = await client.post(
            f"/api/games/join/{invite_code}",
            json={"nickname": "TESTPLAYER"},
        )

        assert join_resp.status_code == 400
        assert "nickname is already taken" in join_resp.json()["detail"]["error"].lower()


class TestGetGameStateEndpoint:
    """Tests for the GET /games/{game_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_game_state_returns_full_state(self, client: AsyncClient) -> None:
        """Test that game state contains all required fields."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        player_id = create_resp.json()["player_id"]

        response = await client.get(f"/api/games/{game_id}?player_id={player_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id
        assert "invite_code" in data
        assert data["phase"] == "lobby"
        assert len(data["players"]) == 1
        assert "config" in data
        assert "my_tiles" in data

    @pytest.mark.asyncio
    async def test_get_game_state_nonexistent_game(self, client: AsyncClient) -> None:
        """Test that requesting non-existent game returns 404."""
        response = await client.get("/api/games/fake-id?player_id=fake-player")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "GAME_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_game_state_nonexistent_player(self, client: AsyncClient) -> None:
        """Test that requesting with invalid player ID returns 404."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]

        response = await client.get(f"/api/games/{game_id}?player_id=invalid-player")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "PLAYER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_game_state_hides_submissions_during_submission_phase(self, client: AsyncClient) -> None:
        """Test that submissions are hidden during submission phase."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        await client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        state_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        state = state_resp.json()

        assert state["phase"] == "round_submission"
        assert state["current_round"]["submissions"] == []


class TestStartGameEndpoint:
    """Tests for the POST /games/{game_id}/start endpoint."""

    @pytest.mark.asyncio
    async def test_start_game_success(self, client: AsyncClient) -> None:
        """Test successfully starting a game."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player_id = create_resp.json()["player_id"]

        await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        response = await client.post(f"/api/games/{game_id}/start?player_id={player_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        state_resp = await client.get(f"/api/games/{game_id}?player_id={player_id}")
        state = state_resp.json()
        assert state["phase"] == "round_submission"

    @pytest.mark.asyncio
    async def test_start_game_nonhost_forbidden(self, client: AsyncClient) -> None:
        """Test that non-host cannot start game."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]

        join_resp = await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        player2_id = join_resp.json()["player_id"]

        response = await client.post(f"/api/games/{game_id}/start?player_id={player2_id}")

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "NOT_HOST"

    @pytest.mark.asyncio
    async def test_start_game_not_enough_players(self, client: AsyncClient) -> None:
        """Test that game cannot start without minimum players."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        player_id = create_resp.json()["player_id"]

        response = await client.post(f"/api/games/{game_id}/start?player_id={player_id}")

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "CANNOT_START"

    @pytest.mark.asyncio
    async def test_start_game_nonexistent_game(self, client: AsyncClient) -> None:
        """Test starting non-existent game returns 404."""
        response = await client.post("/api/games/fake-id/start?player_id=fake-player")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_game_distributes_tiles(self, client: AsyncClient) -> None:
        """Test that starting game distributes tiles to players."""
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player_id = create_resp.json()["player_id"]

        await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        await client.post(f"/api/games/{game_id}/start?player_id={player_id}")

        state_resp = await client.get(f"/api/games/{game_id}?player_id={player_id}")
        state = state_resp.json()
        tiles_per_player = state["config"]["tiles_per_player"]
        assert len(state["my_tiles"]) == tiles_per_player


class TestSubmitResponseEndpoint:
    """Tests for the POST /games/{game_id}/submit endpoint."""

    @pytest.fixture
    async def started_game(self, client: AsyncClient):
        """Create and start a game with two players.

        Note: In the new flow, judge is not selected until all players submit.
        """
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        player2_id = join_resp.json()["player_id"]

        await client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        return {
            "game_id": game_id,
            "player1_id": player1_id,
            "player2_id": player2_id,
        }

    @pytest.mark.asyncio
    async def test_submit_response_success(self, client: AsyncClient, started_game) -> None:
        """Test successfully submitting a response."""
        game_id = started_game["game_id"]
        player_id = started_game["player1_id"]

        state_resp = await client.get(f"/api/games/{game_id}?player_id={player_id}")
        state = state_resp.json()
        tiles = state["my_tiles"][:2]

        response = await client.post(
            f"/api/games/{game_id}/submit?player_id={player_id}",
            json={"tiles_used": tiles},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_submit_removes_used_tiles(self, client: AsyncClient, started_game) -> None:
        """Test that submitted tiles are removed from player's hand."""
        game_id = started_game["game_id"]
        player_id = started_game["player1_id"]

        state_before_resp = await client.get(f"/api/games/{game_id}?player_id={player_id}")
        state_before = state_before_resp.json()
        tiles_before = set(state_before["my_tiles"])
        tiles_to_use = state_before["my_tiles"][:2]

        await client.post(
            f"/api/games/{game_id}/submit?player_id={player_id}",
            json={"tiles_used": tiles_to_use},
        )

        state_after_resp = await client.get(f"/api/games/{game_id}?player_id={player_id}")
        state_after = state_after_resp.json()
        tiles_after = set(state_after["my_tiles"])

        for tile in tiles_to_use:
            assert tile not in tiles_after
        assert len(tiles_after) == len(tiles_before) - 2

    @pytest.mark.asyncio
    async def test_all_players_can_submit(self, client: AsyncClient, started_game) -> None:
        """Test that all players can submit (no judge restriction)."""
        game_id = started_game["game_id"]
        player1_id = started_game["player1_id"]
        player2_id = started_game["player2_id"]

        # Both players should be able to submit
        state1_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        state2_resp = await client.get(f"/api/games/{game_id}?player_id={player2_id}")
        state1 = state1_resp.json()
        state2 = state2_resp.json()

        resp1 = await client.post(
            f"/api/games/{game_id}/submit?player_id={player1_id}",
            json={"tiles_used": state1["my_tiles"][:1]},
        )
        assert resp1.status_code == 200

        resp2 = await client.post(
            f"/api/games/{game_id}/submit?player_id={player2_id}",
            json={"tiles_used": state2["my_tiles"][:1]},
        )
        assert resp2.status_code == 200

        # After both submit, game should be in judging phase with judge selected
        final_state_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        final_state = final_state_resp.json()
        assert final_state["phase"] == "round_judging"
        assert final_state["current_round"]["judge_id"] is not None

    @pytest.mark.asyncio
    async def test_cannot_submit_invalid_tiles(self, client: AsyncClient, started_game) -> None:
        """Test that submitting tiles not in hand fails."""
        game_id = started_game["game_id"]
        player_id = started_game["player1_id"]

        response = await client.post(
            f"/api/games/{game_id}/submit?player_id={player_id}",
            json={"tiles_used": ["FAKE_TILE"]},
        )

        assert response.status_code == 400


class TestSelectWinnerEndpoint:
    """Tests for the POST /games/{game_id}/judge endpoint."""

    @pytest.fixture
    async def judging_game(self, client: AsyncClient):
        """Create a game in judging phase.

        In the new flow: all players submit, then judge is selected.
        """
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        player2_id = join_resp.json()["player_id"]

        await client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Both players submit (new flow - everyone submits)
        state1_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        state2_resp = await client.get(f"/api/games/{game_id}?player_id={player2_id}")
        state1 = state1_resp.json()
        state2 = state2_resp.json()

        await client.post(
            f"/api/games/{game_id}/submit?player_id={player1_id}",
            json={"tiles_used": state1["my_tiles"][:1]},
        )
        await client.post(
            f"/api/games/{game_id}/submit?player_id={player2_id}",
            json={"tiles_used": state2["my_tiles"][:1]},
        )

        # Now judge is selected and game is in judging phase
        final_state_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        final_state = final_state_resp.json()
        judge_id = final_state["current_round"]["judge_id"]
        non_judge_id = player1_id if judge_id == player2_id else player2_id

        return {
            "game_id": game_id,
            "player1_id": player1_id,
            "player2_id": player2_id,
            "judge_id": judge_id,
            "non_judge_id": non_judge_id,
        }

    @pytest.mark.asyncio
    async def test_select_winner_success(self, client: AsyncClient, judging_game) -> None:
        """Test judge successfully selecting winner."""
        game_id = judging_game["game_id"]
        judge_id = judging_game["judge_id"]
        non_judge_id = judging_game["non_judge_id"]

        response = await client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": non_judge_id},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        state_resp = await client.get(f"/api/games/{game_id}?player_id={judge_id}")
        state = state_resp.json()
        assert state["phase"] == "round_results"
        assert state["current_round"]["winner_id"] == non_judge_id

    @pytest.mark.asyncio
    async def test_nonjudge_cannot_select_winner(self, client: AsyncClient, judging_game) -> None:
        """Test that non-judge cannot select winner."""
        game_id = judging_game["game_id"]
        non_judge_id = judging_game["non_judge_id"]

        response = await client.post(
            f"/api/games/{game_id}/judge?player_id={non_judge_id}",
            json={"winner_player_id": non_judge_id},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "NOT_JUDGE"

    @pytest.mark.asyncio
    async def test_winner_score_increases(self, client: AsyncClient, judging_game) -> None:
        """Test that winner's score increases by 1."""
        game_id = judging_game["game_id"]
        judge_id = judging_game["judge_id"]
        non_judge_id = judging_game["non_judge_id"]

        state_before_resp = await client.get(f"/api/games/{game_id}?player_id={non_judge_id}")
        state_before = state_before_resp.json()
        score_before = next(p["score"] for p in state_before["players"] if p["id"] == non_judge_id)

        await client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": non_judge_id},
        )

        state_after_resp = await client.get(f"/api/games/{game_id}?player_id={non_judge_id}")
        state_after = state_after_resp.json()
        score_after = next(p["score"] for p in state_after["players"] if p["id"] == non_judge_id)

        assert score_after == score_before + 1


class TestAdvanceRoundEndpoint:
    """Tests for the POST /games/{game_id}/advance endpoint."""

    @pytest.fixture
    async def results_game(self, client: AsyncClient):
        """Create a game in results phase.

        In the new flow: all players submit, then judge is selected, then winner is picked.
        """
        create_resp = await client.post("/api/games", json={"host_nickname": "Host"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = await client.post(f"/api/games/join/{invite_code}", json={"nickname": "Player2"})
        player2_id = join_resp.json()["player_id"]

        await client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Both players submit
        state1_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        state2_resp = await client.get(f"/api/games/{game_id}?player_id={player2_id}")
        state1 = state1_resp.json()
        state2 = state2_resp.json()

        await client.post(
            f"/api/games/{game_id}/submit?player_id={player1_id}",
            json={"tiles_used": state1["my_tiles"][:1]},
        )
        await client.post(
            f"/api/games/{game_id}/submit?player_id={player2_id}",
            json={"tiles_used": state2["my_tiles"][:1]},
        )

        # Now in judging phase, get judge and pick winner
        judging_state_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        judging_state = judging_state_resp.json()
        judge_id = judging_state["current_round"]["judge_id"]
        non_judge_id = player1_id if judge_id == player2_id else player2_id

        await client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": non_judge_id},
        )

        return {
            "game_id": game_id,
            "player1_id": player1_id,
            "player2_id": player2_id,
            "judge_id": judge_id,
            "winner_id": non_judge_id,
        }

    @pytest.mark.asyncio
    async def test_advance_round_success(self, client: AsyncClient, results_game) -> None:
        """Test host successfully advancing to next round."""
        game_id = results_game["game_id"]
        player1_id = results_game["player1_id"]

        response = await client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_advance_round_starts_new_round(self, client: AsyncClient, results_game) -> None:
        """Test that advancing starts a new round."""
        game_id = results_game["game_id"]
        player1_id = results_game["player1_id"]

        state_before_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        state_before = state_before_resp.json()
        round_before = state_before["current_round"]["round_number"]

        await client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")

        state_after_resp = await client.get(f"/api/games/{game_id}?player_id={player1_id}")
        state_after = state_after_resp.json()

        if state_after["phase"] != "game_over":
            assert state_after["phase"] == "round_submission"
            assert state_after["current_round"]["round_number"] == round_before + 1

    @pytest.mark.asyncio
    async def test_nonhost_cannot_advance(self, client: AsyncClient, results_game) -> None:
        """Test that non-host cannot advance round."""
        game_id = results_game["game_id"]
        player2_id = results_game["player2_id"]

        response = await client.post(f"/api/games/{game_id}/advance?player_id={player2_id}")

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "NOT_HOST"

    @pytest.mark.asyncio
    async def test_tiles_replenished_after_advance(self, client: AsyncClient, results_game) -> None:
        """Test that tiles are replenished after advancing."""
        game_id = results_game["game_id"]
        player1_id = results_game["player1_id"]
        winner_id = results_game["winner_id"]

        await client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")

        state_resp = await client.get(f"/api/games/{game_id}?player_id={winner_id}")
        state = state_resp.json()

        if state["phase"] != "game_over":
            tiles_per_player = state["config"]["tiles_per_player"]
            assert len(state["my_tiles"]) == tiles_per_player
