"""End-to-end tests for playing a complete game."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.store import clear_store


@pytest.fixture(autouse=True)
def clean_store():
    """Clear the game store before each test."""
    clear_store()
    yield
    clear_store()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestGameE2E:
    """End-to-end tests for a complete game flow."""

    def test_two_player_game_to_completion(self, client: TestClient):
        """Test a complete game with two players playing to victory."""
        # Player 1 creates a game
        create_response = client.post(
            "/api/games",
            json={"host_nickname": "Alice"},
        )
        assert create_response.status_code == 200
        game_data = create_response.json()
        game_id = game_data["game_id"]
        invite_code = game_data["invite_code"]
        player1_id = game_data["player_id"]

        # Player 2 joins the game
        join_response = client.post(
            f"/api/games/join/{invite_code}",
            json={"nickname": "Bob"},
        )
        assert join_response.status_code == 200
        player2_id = join_response.json()["player_id"]

        # Verify both players are in the lobby
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert state["phase"] == "lobby"
        assert len(state["players"]) == 2

        # Host starts the game
        start_response = client.post(f"/api/games/{game_id}/start?player_id={player1_id}")
        assert start_response.status_code == 200

        # Verify game is in submission phase
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert state["phase"] == "round_submission"
        assert state["current_round"] is not None
        assert state["current_round"]["round_number"] == 1

        # Play rounds until someone wins
        rounds_played = 0
        max_rounds = 10  # Safety limit

        while rounds_played < max_rounds:
            rounds_played += 1

            # Get current state for both players
            state1 = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
            state2 = client.get(f"/api/games/{game_id}?player_id={player2_id}").json()

            if state1["phase"] == "game_over":
                break

            assert state1["phase"] == "round_submission"

            judge_id = state1["current_round"]["judge_id"]
            submitter_id = player1_id if judge_id == player2_id else player2_id
            submitter_state = state1 if submitter_id == player1_id else state2

            # Submitter submits a response using their tiles
            tiles_to_use = submitter_state["my_tiles"][:2]  # Use first 2 tiles
            submit_response = client.post(
                f"/api/games/{game_id}/submit?player_id={submitter_id}",
                json={"tiles_used": tiles_to_use},
            )
            assert submit_response.status_code == 200

            # Verify we're now in judging phase
            state = client.get(f"/api/games/{game_id}?player_id={judge_id}").json()
            assert state["phase"] == "round_judging"
            assert len(state["current_round"]["submissions"]) == 1

            # Judge selects the winner (only one submission)
            judge_response = client.post(
                f"/api/games/{game_id}/judge?player_id={judge_id}",
                json={"winner_player_id": submitter_id},
            )
            assert judge_response.status_code == 200

            # Verify we're in results phase
            state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
            assert state["phase"] == "round_results"
            assert state["current_round"]["winner_id"] == submitter_id

            # Check if game should be over
            winner_score = next(p["score"] for p in state["players"] if p["id"] == submitter_id)
            points_to_win = state["config"]["points_to_win"]

            # Host advances to next round
            advance_response = client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")
            assert advance_response.status_code == 200

            # Check final state
            state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()

            if winner_score >= points_to_win:
                assert state["phase"] == "game_over"
                break

            assert state["phase"] == "round_submission"

        # Verify game ended properly
        final_state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert final_state["phase"] == "game_over"

        # Verify someone won
        scores = [p["score"] for p in final_state["players"]]
        assert max(scores) >= final_state["config"]["points_to_win"]

    def test_judge_rotation(self, client: TestClient):
        """Test that the judge rotates between players each round."""
        # Create game and add player
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp.json()["player_id"]

        # Start game
        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        judges_seen = []

        # Play 3 rounds to verify rotation
        for _ in range(3):
            state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()

            if state["phase"] == "game_over":
                break

            judge_id = state["current_round"]["judge_id"]
            judges_seen.append(judge_id)

            # Submit and judge
            submitter_id = player1_id if judge_id == player2_id else player2_id
            submitter_state = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()

            client.post(
                f"/api/games/{game_id}/submit?player_id={submitter_id}",
                json={"tiles_used": submitter_state["my_tiles"][:1]},
            )
            client.post(
                f"/api/games/{game_id}/judge?player_id={judge_id}",
                json={"winner_player_id": submitter_id},
            )
            client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")

        # Verify judges alternated
        if len(judges_seen) >= 2:
            assert judges_seen[0] != judges_seen[1], "Judge should rotate"

    def test_tiles_replenished_after_round(self, client: TestClient):
        """Test that player tiles are replenished after using them."""
        # Create and start game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp.json()["player_id"]

        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get initial state
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        initial_tile_count = len(state["my_tiles"])
        tiles_per_player = state["config"]["tiles_per_player"]

        assert initial_tile_count == tiles_per_player

        # Find who's not the judge and submit
        judge_id = state["current_round"]["judge_id"]
        submitter_id = player1_id if judge_id == player2_id else player2_id

        submitter_state = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()
        tiles_to_use = submitter_state["my_tiles"][:3]

        client.post(
            f"/api/games/{game_id}/submit?player_id={submitter_id}",
            json={"tiles_used": tiles_to_use},
        )

        # Verify tiles were removed
        state_after_submit = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()
        assert len(state_after_submit["my_tiles"]) == tiles_per_player - 3

        # Complete round
        client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": submitter_id},
        )
        client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")

        # Verify tiles were replenished
        state_after_round = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()

        if state_after_round["phase"] != "game_over":
            assert len(state_after_round["my_tiles"]) == tiles_per_player

    def test_only_host_can_start_and_advance(self, client: TestClient):
        """Test that only the host can start the game and advance rounds."""
        # Create game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp.json()["player_id"]

        # Non-host tries to start - should fail
        start_resp = client.post(f"/api/games/{game_id}/start?player_id={player2_id}")
        assert start_resp.status_code == 403

        # Host starts successfully
        start_resp = client.post(f"/api/games/{game_id}/start?player_id={player1_id}")
        assert start_resp.status_code == 200

        # Play through a round
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        judge_id = state["current_round"]["judge_id"]
        submitter_id = player1_id if judge_id == player2_id else player2_id

        submitter_state = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()

        client.post(
            f"/api/games/{game_id}/submit?player_id={submitter_id}",
            json={"tiles_used": submitter_state["my_tiles"][:1]},
        )
        client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": submitter_id},
        )

        # Non-host tries to advance - should fail
        advance_resp = client.post(f"/api/games/{game_id}/advance?player_id={player2_id}")
        assert advance_resp.status_code == 403

        # Host advances successfully
        advance_resp = client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")
        assert advance_resp.status_code == 200

    def test_only_judge_can_select_winner(self, client: TestClient):
        """Test that only the current judge can select the round winner."""
        # Create and start game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp.json()["player_id"]

        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get judge and submitter
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        judge_id = state["current_round"]["judge_id"]
        submitter_id = player1_id if judge_id == player2_id else player2_id

        # Submit response
        submitter_state = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()
        client.post(
            f"/api/games/{game_id}/submit?player_id={submitter_id}",
            json={"tiles_used": submitter_state["my_tiles"][:1]},
        )

        # Non-judge tries to select winner - should fail
        judge_resp = client.post(
            f"/api/games/{game_id}/judge?player_id={submitter_id}",
            json={"winner_player_id": submitter_id},
        )
        assert judge_resp.status_code == 403

        # Judge selects successfully
        judge_resp = client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": submitter_id},
        )
        assert judge_resp.status_code == 200

    def test_three_player_game_with_multiple_submissions(self, client: TestClient):
        """Test a game with three players where judge picks from multiple submissions."""
        # Create game with host
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        # Add two more players
        join_resp2 = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp2.json()["player_id"]

        join_resp3 = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Charlie"})
        player3_id = join_resp3.json()["player_id"]

        # Verify all three players in lobby
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert len(state["players"]) == 3

        # Start game
        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get state to find judge and submitters
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert state["phase"] == "round_submission"

        judge_id = state["current_round"]["judge_id"]
        submitter_ids = [pid for pid in [player1_id, player2_id, player3_id] if pid != judge_id]
        assert len(submitter_ids) == 2

        # Both non-judge players submit
        for submitter_id in submitter_ids:
            submitter_state = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()
            submit_resp = client.post(
                f"/api/games/{game_id}/submit?player_id={submitter_id}",
                json={"tiles_used": submitter_state["my_tiles"][:2]},
            )
            assert submit_resp.status_code == 200

        # Verify game is now in judging phase with 2 submissions
        state = client.get(f"/api/games/{game_id}?player_id={judge_id}").json()
        assert state["phase"] == "round_judging"
        assert len(state["current_round"]["submissions"]) == 2

        # Judge picks a winner
        winner_id = submitter_ids[0]
        judge_resp = client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": winner_id},
        )
        assert judge_resp.status_code == 200

        # Verify results
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert state["phase"] == "round_results"
        assert state["current_round"]["winner_id"] == winner_id

        # Verify winner score increased
        winner_score = next(p["score"] for p in state["players"] if p["id"] == winner_id)
        assert winner_score == 1

    def test_cannot_join_game_after_start(self, client: TestClient):
        """Test that players cannot join a game that has already started."""
        # Create game with two players
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})

        # Start the game
        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Try to join after start - should fail
        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Charlie"})
        assert join_resp.status_code == 400
        assert "lobby" in join_resp.json()["detail"]["error"].lower()

    def test_judge_cannot_submit(self, client: TestClient):
        """Test that the judge cannot submit a response."""
        # Create and start game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})

        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get the judge
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        judge_id = state["current_round"]["judge_id"]

        # Get judge's tiles
        judge_state = client.get(f"/api/games/{game_id}?player_id={judge_id}").json()

        # Judge tries to submit - should fail
        submit_resp = client.post(
            f"/api/games/{game_id}/submit?player_id={judge_id}",
            json={"tiles_used": judge_state["my_tiles"][:1]},
        )
        assert submit_resp.status_code == 400
        assert "judge" in submit_resp.json()["detail"]["error"].lower()

    def test_player_cannot_submit_twice(self, client: TestClient):
        """Test that a player cannot submit more than once per round."""
        # Create game with 3 players so we have time to test double submit
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp2 = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp2.json()["player_id"]

        client.post(f"/api/games/join/{invite_code}", json={"nickname": "Charlie"})

        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get state and find a non-judge player
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        judge_id = state["current_round"]["judge_id"]
        submitter_id = player1_id if judge_id != player1_id else player2_id

        submitter_state = client.get(f"/api/games/{game_id}?player_id={submitter_id}").json()

        # First submission - should succeed
        submit_resp = client.post(
            f"/api/games/{game_id}/submit?player_id={submitter_id}",
            json={"tiles_used": submitter_state["my_tiles"][:1]},
        )
        assert submit_resp.status_code == 200

        # Second submission - should fail
        submit_resp2 = client.post(
            f"/api/games/{game_id}/submit?player_id={submitter_id}",
            json={"tiles_used": submitter_state["my_tiles"][1:2]},
        )
        assert submit_resp2.status_code == 400
        assert "already submitted" in submit_resp2.json()["detail"]["error"].lower()

    def test_cannot_start_with_insufficient_players(self, client: TestClient):
        """Test that game cannot start without minimum players."""
        # Create game with only host
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        player1_id = create_resp.json()["player_id"]

        # Try to start with only one player - should fail
        start_resp = client.post(f"/api/games/{game_id}/start?player_id={player1_id}")
        assert start_resp.status_code == 400
        assert "not enough" in start_resp.json()["detail"]["error"].lower()

    def test_game_full_prevention(self, client: TestClient):
        """Test that players cannot join when game is full."""
        # Create game with max_players=2
        create_resp = client.post(
            "/api/games",
            json={
                "host_nickname": "Alice",
                "config": {"max_players": 2},
            },
        )
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]

        # Second player joins successfully
        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        assert join_resp.status_code == 200

        # Third player cannot join - game is full
        join_resp2 = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Charlie"})
        assert join_resp2.status_code == 400
        assert "full" in join_resp2.json()["detail"]["error"].lower()

        # Verify only 2 players in game
        player1_id = create_resp.json()["player_id"]
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        assert len(state["players"]) == 2

    def test_cannot_submit_tiles_player_does_not_have(self, client: TestClient):
        """Test that a player cannot submit tiles they don't possess."""
        # Create and start game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})

        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get state
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        judge_id = state["current_round"]["judge_id"]

        # Try to submit a tile the player doesn't have
        player1_id = player1_id if judge_id != player1_id else create_resp.json()["player_id"]
        submit_resp = client.post(
            f"/api/games/{game_id}/submit?player_id={player1_id}",
            json={"tiles_used": ["FAKE_TILE_THAT_DOESNT_EXIST"]},
        )
        # Either 400 if player is valid but tile invalid, or 404/400 otherwise
        assert submit_resp.status_code in [400, 403]

    def test_custom_game_configuration(self, client: TestClient):
        """Test that custom game configuration is applied correctly."""
        custom_config = {
            "tiles_per_player": 10,
            "points_to_win": 3,
            "min_players": 2,
            "max_players": 4,
        }

        create_resp = client.post(
            "/api/games",
            json={"host_nickname": "Alice", "config": custom_config},
        )
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})

        # Start and verify config
        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()

        assert state["config"]["tiles_per_player"] == 10
        assert state["config"]["points_to_win"] == 3
        assert state["config"]["max_players"] == 4
        assert len(state["my_tiles"]) == 10

    def test_cannot_select_nonsubmitter_as_winner(self, client: TestClient):
        """Test that the judge cannot select a player who didn't submit."""
        # Create game with 3 players
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp2 = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp2.json()["player_id"]

        join_resp3 = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Charlie"})
        player3_id = join_resp3.json()["player_id"]

        client.post(f"/api/games/{game_id}/start?player_id={player1_id}")

        # Get state
        state = client.get(f"/api/games/{game_id}?player_id={player1_id}").json()
        judge_id = state["current_round"]["judge_id"]

        # Find submitters (non-judges)
        all_players = [player1_id, player2_id, player3_id]
        submitters = [p for p in all_players if p != judge_id]

        # Only one player submits
        submitter_state = client.get(f"/api/games/{game_id}?player_id={submitters[0]}").json()
        client.post(
            f"/api/games/{game_id}/submit?player_id={submitters[0]}",
            json={"tiles_used": submitter_state["my_tiles"][:1]},
        )

        # Second player also submits to trigger judging phase
        submitter2_state = client.get(f"/api/games/{game_id}?player_id={submitters[1]}").json()
        client.post(
            f"/api/games/{game_id}/submit?player_id={submitters[1]}",
            json={"tiles_used": submitter2_state["my_tiles"][:1]},
        )

        # Judge tries to select the judge (who didn't submit) as winner
        judge_resp = client.post(
            f"/api/games/{game_id}/judge?player_id={judge_id}",
            json={"winner_player_id": judge_id},
        )
        assert judge_resp.status_code == 400
        assert "submitted" in judge_resp.json()["detail"]["error"].lower()

    def test_game_not_found_errors(self, client: TestClient):
        """Test that appropriate errors are returned for non-existent games."""
        fake_game_id = "nonexistent-game-id"
        fake_player_id = "nonexistent-player-id"

        # Get game state
        resp = client.get(f"/api/games/{fake_game_id}?player_id={fake_player_id}")
        assert resp.status_code == 404

        # Start game
        resp = client.post(f"/api/games/{fake_game_id}/start?player_id={fake_player_id}")
        assert resp.status_code == 404

        # Submit response
        resp = client.post(
            f"/api/games/{fake_game_id}/submit?player_id={fake_player_id}",
            json={"tiles_used": ["test"]},
        )
        assert resp.status_code == 404

        # Join with invalid invite code
        resp = client.post("/api/games/join/INVALID", json={"nickname": "Test"})
        assert resp.status_code == 404

    def test_error_responses_contain_helpful_info(self, client: TestClient):
        """Test that error responses contain error code and message for debugging."""
        # Create game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        player1_id = create_resp.json()["player_id"]

        # Try to start with only one player - verify error format
        start_resp = client.post(f"/api/games/{game_id}/start?player_id={player1_id}")
        assert start_resp.status_code == 400
        error_detail = start_resp.json()["detail"]
        assert "error" in error_detail
        assert "code" in error_detail
        assert error_detail["code"] == "CANNOT_START"
        assert "not enough" in error_detail["error"].lower()

    def test_player_not_found_in_game_error(self, client: TestClient):
        """Test that requesting game state with invalid player ID returns proper error."""
        # Create game
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]

        # Try to get state with non-existent player
        resp = client.get(f"/api/games/{game_id}?player_id=invalid-player-id")
        assert resp.status_code == 404
        error_detail = resp.json()["detail"]
        assert error_detail["code"] == "PLAYER_NOT_FOUND"

    def test_wrong_phase_errors(self, client: TestClient):
        """Test that actions in wrong phase return descriptive errors."""
        # Create game with two players
        create_resp = client.post("/api/games", json={"host_nickname": "Alice"})
        game_id = create_resp.json()["game_id"]
        invite_code = create_resp.json()["invite_code"]
        player1_id = create_resp.json()["player_id"]

        join_resp = client.post(f"/api/games/join/{invite_code}", json={"nickname": "Bob"})
        player2_id = join_resp.json()["player_id"]

        # Try to submit before game starts (still in lobby)
        submit_resp = client.post(
            f"/api/games/{game_id}/submit?player_id={player2_id}",
            json={"tiles_used": ["test"]},
        )
        assert submit_resp.status_code == 400
        assert "submission" in submit_resp.json()["detail"]["error"].lower()

        # Try to advance before game starts
        advance_resp = client.post(f"/api/games/{game_id}/advance?player_id={player1_id}")
        assert advance_resp.status_code == 400
        assert "results" in advance_resp.json()["detail"]["error"].lower()
