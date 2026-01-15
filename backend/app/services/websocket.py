"""WebSocket connection manager for real-time game communication.

This module demonstrates key WebSocket concepts:
1. Connection management (accepting, tracking, removing connections)
2. Broadcasting messages to multiple clients
3. Handling disconnections gracefully
"""

import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for all games.

    Key Concepts:
    - Each game has multiple players
    - Each player has one WebSocket connection
    - We need to track which connection belongs to which player in which game
    - We need to send messages to all players in a game (broadcast)
    """

    def __init__(self) -> None:
        # Structure: {game_id: {player_id: WebSocket}}
        # This nested dict lets us:
        # 1. Find all connections in a game (for broadcasting)
        # 2. Find a specific player's connection (for direct messages)
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, game_id: str, player_id: str, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and track it.

        WebSocket Concept: Before we can use a WebSocket, we must 'accept' it.
        This completes the WebSocket handshake (HTTP upgrade).

        Args:
            game_id: Which game this connection belongs to
            player_id: Which player this connection belongs to
            websocket: The WebSocket connection object
        """
        await websocket.accept()  # Complete the WebSocket handshake

        # Create the game's connection dict if it doesn't exist
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}

        # Store the connection
        self.active_connections[game_id][player_id] = websocket

    def disconnect(self, game_id: str, player_id: str) -> None:
        """Remove a connection from tracking.

        WebSocket Concept: When a client disconnects (intentionally or due to
        error), we need to clean up our tracking to avoid memory leaks and
        sending to dead connections.
        """
        if game_id in self.active_connections:
            self.active_connections[game_id].pop(player_id, None)

            # Clean up empty game dicts
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def send_personal_message(self, message: dict[str, Any], game_id: str, player_id: str) -> None:
        """Send a message to a specific player.

        TypeScript Parallel: This is like calling a specific callback function.
        WebSocket Concept: send_json() serializes a Python dict to JSON and sends it.

        Args:
            message: The data to send (will be converted to JSON)
            game_id: Which game the player is in
            player_id: Which player to send to
        """
        if game_id in self.active_connections:
            websocket = self.active_connections[game_id].get(player_id)
            if websocket:
                await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any], game_id: str) -> None:
        """Send a message to ALL players in a game.

        This is the key benefit of WebSockets for multiplayer games!
        When something happens (player joins, game starts, etc.),
        we can instantly notify everyone.

        TypeScript Parallel: Like calling Array.forEach() to notify all subscribers.

        Args:
            message: The data to send to everyone
            game_id: Which game's players to notify
        """
        if game_id in self.active_connections:
            # Loop through all players in the game
            for player_id, websocket in self.active_connections[game_id].items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    # If sending fails, the connection is probably dead
                    # In production, you'd want to remove it from active_connections
                    log.error(f"Error broadcasting to connection: {e}")
                    self.disconnect(game_id, player_id)

    async def broadcast_except(self, message: dict[str, Any], game_id: str, exclude_player_id: str) -> None:
        """Send a message to all players EXCEPT one.

        Useful when you want to notify others about what a player did,
        but that player already knows (they triggered the action).

        Example: When Alice submits her answer, we tell everyone else
        "Alice submitted" but we tell Alice "Submission received".
        """
        if game_id in self.active_connections:
            for player_id, websocket in self.active_connections[game_id].items():
                if player_id != exclude_player_id:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        print(f"Error broadcasting to connection: {e}")

    def get_connected_players(self, game_id: str) -> list[str]:
        """Get list of currently connected player IDs for a game.

        Useful for checking who's still in the game.
        """
        if game_id in self.active_connections:
            return list(self.active_connections[game_id].keys())
        return []

    async def send_heartbeat(self) -> None:
        """Send a heartbeat ping to all connected clients.

        This keeps WebSocket connections alive through load balancers
        and proxies that may close idle connections.
        """
        # Create a snapshot of connections to iterate over
        # (avoids issues if connections change during iteration)
        connections_snapshot: list[tuple[str, str, WebSocket]] = []
        for game_id, players in list(self.active_connections.items()):
            for player_id, websocket in list(players.items()):
                connections_snapshot.append((game_id, player_id, websocket))

        for game_id, player_id, websocket in connections_snapshot:
            try:
                await websocket.send_json({"type": "ping"})
            except Exception as e:
                log.warning(f"Heartbeat failed for {game_id}/{player_id}: {e}")
                self.disconnect(game_id, player_id)


# Singleton instance - one manager for the whole application
# This ensures all endpoints share the same connection tracking
manager = ConnectionManager()
