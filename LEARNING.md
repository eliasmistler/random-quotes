# Upgrading to WebSockets: A Hands-On Guide

This guide walks you through replacing the 2-second polling with WebSockets. Code snippets are intentionally brief - you'll learn more by figuring out the details yourself.

## Overview

**Current approach**: Views poll `refreshGameState()` every 2 seconds
**Target approach**: Server pushes updates to all connected clients instantly

```
Before: Client → GET /games/{id} → Server (every 2s, per client)
After:  Server → WebSocket → All Clients (on state change, once)
```

---

## Part 1: Backend - Connection Manager

Create a new file `backend/app/services/websocket.py` to manage WebSocket connections.

### 1.1 ConnectionManager Class

You need a class that:
- Stores active connections grouped by `game_id`
- Has methods: `connect()`, `disconnect()`, `broadcast()`

```python
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Hint: dict of game_id -> list of WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}
```

**Your tasks:**
1. Implement `async def connect(self, game_id: str, websocket: WebSocket)`
   - Accept the WebSocket connection
   - Add it to the list for that game_id

2. Implement `def disconnect(self, game_id: str, websocket: WebSocket)`
   - Remove the connection from the list
   - Clean up empty game entries

3. Implement `async def broadcast(self, game_id: str, message: dict)`
   - Send the message to ALL connections for that game_id
   - Handle any disconnected clients gracefully

Create a singleton instance at the bottom:
```python
manager = ConnectionManager()
```

---

## Part 2: Backend - WebSocket Endpoint

Add a WebSocket route in `backend/app/api/routes.py`.

### 2.1 Basic Endpoint

```python
from fastapi import WebSocket, WebSocketDisconnect
from app.services.websocket import manager

@router.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str, player_id: str):
    # 1. Connect
    await manager.connect(game_id, websocket)
    try:
        # 2. Keep connection alive, listen for messages
        while True:
            data = await websocket.receive_json()
            # For now, just echo or ignore
    except WebSocketDisconnect:
        # 3. Clean up on disconnect
        manager.disconnect(game_id, websocket)
```

### 2.2 Broadcast on State Changes

When game state changes (player joins, submits, etc.), broadcast to all players.

Find places in your routes where state changes occur and add:
```python
await manager.broadcast(game_id, {"type": "game_update"})
```

Key locations to add broadcasts:
- `join_game_route` - when a player joins
- `start_game_route` - when game starts
- `submit_response_route` - when a player submits
- `select_winner_route` - when winner is chosen
- `advance_round_route` - when round advances

---

## Part 3: Frontend - WebSocket Service

Create `frontend/src/services/websocket.ts`.

### 3.1 Basic WebSocket Class

```typescript
type MessageHandler = (data: unknown) => void

export class GameWebSocket {
  private ws: WebSocket | null = null
  private messageHandler: MessageHandler | null = null

  connect(gameId: string, playerId: string): void {
    const url = `ws://localhost:8000/api/ws/game/${gameId}?player_id=${playerId}`
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      // Parse JSON and call handler
    }

    this.ws.onclose = () => {
      // Handle reconnection?
    }
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandler = handler
  }

  disconnect(): void {
    // Close the connection
  }
}
```

**Your tasks:**
1. Complete `onmessage` to parse JSON and call the handler
2. Implement `disconnect()` to close cleanly
3. Consider: What happens if connection drops? Add reconnection logic?

---

## Part 4: Integrate with Pinia Store

Update `frontend/src/stores/game.ts` to use WebSockets.

### 4.1 Add WebSocket to Store

```typescript
import { GameWebSocket } from '@/services/websocket'

// Inside defineStore:
const ws = new GameWebSocket()

function connectWebSocket() {
  if (!gameId.value || !playerId.value) return

  ws.onMessage(async (data) => {
    // When we receive an update, refresh state
    if ((data as {type: string}).type === 'game_update') {
      await refreshGameState()
    }
  })

  ws.connect(gameId.value, playerId.value)
}
```

### 4.2 Connect After Join/Create

Call `connectWebSocket()` at the end of:
- `createGame()`
- `joinGame()`

### 4.3 Disconnect on Leave

Update `leaveGame()`:
```typescript
function leaveGame() {
  ws.disconnect()
  // ... existing cleanup
}
```

---

## Part 5: Remove Polling from Views

### 5.1 LobbyView.vue

Remove:
- `pollingInterval` ref
- `setInterval` in `onMounted`
- `clearInterval` in `onUnmounted`

### 5.2 GameView.vue

Remove the same polling code. Keep the timer interval for the countdown (that's different - it's UI-only).

---

## Part 6: Testing

### Manual Testing Checklist

1. **Basic connection test**
   - Open browser DevTools → Network → WS tab
   - Create/join a game
   - Verify WebSocket connection appears and stays "101 Switching Protocols"

2. **Multi-client test**
   - Open two browser windows (or incognito)
   - Create game in window 1, join in window 2
   - Verify both see player list update instantly (no 2s delay)

3. **Disconnect handling**
   - Connect, then stop the backend server
   - Check browser console for errors
   - Restart server, verify reconnection (if implemented)

4. **Full game flow test**
   - Play through a complete game with 2+ windows
   - Verify all transitions happen simultaneously:
     - Game start
     - Submissions appearing for judge
     - Winner announcement
     - Score updates

### Automated Testing - Backend

Create `backend/tests/test_websocket.py`:

```python
import pytest
from fastapi.testclient import TestClient

def test_websocket_connects(client: TestClient):
    """Test that WebSocket connection can be established."""
    # First create a game via REST to get game_id and player_id
    response = client.post("/api/games", json={"host_nickname": "TestHost"})
    data = response.json()
    game_id = data["game_id"]
    player_id = data["player_id"]

    # Now test WebSocket connection
    with client.websocket_connect(
        f"/api/ws/game/{game_id}?player_id={player_id}"
    ) as websocket:
        # Connection succeeded if we get here
        # Optionally send/receive a test message
        pass

def test_broadcast_on_player_join(client: TestClient):
    """Test that existing players receive broadcast when new player joins."""
    # 1. Create game, get credentials
    # 2. Connect player 1 via WebSocket
    # 3. Join player 2 via REST API
    # 4. Assert player 1's WebSocket received a message
    pass  # Implement this!
```

**Hint**: `TestClient.websocket_connect()` returns a context manager. Use `websocket.receive_json()` to wait for messages.

### Automated Testing - Frontend (Optional)

If you want to unit test the WebSocket service with Vitest:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GameWebSocket } from '@/services/websocket'

describe('GameWebSocket', () => {
  let mockWs: { onmessage: any; close: any }

  beforeEach(() => {
    mockWs = { onmessage: null, close: vi.fn() }
    vi.stubGlobal('WebSocket', vi.fn(() => mockWs))
  })

  it('calls handler when message received', () => {
    const ws = new GameWebSocket()
    const handler = vi.fn()

    ws.onMessage(handler)
    ws.connect('game123', 'player456')

    // Simulate receiving a message
    mockWs.onmessage({ data: JSON.stringify({ type: 'game_update' }) })

    expect(handler).toHaveBeenCalledWith({ type: 'game_update' })
  })
})
```

---

## Debugging Tips

1. **Browser DevTools**
   - Network tab → WS filter → Click connection → Messages tab
   - See all sent/received WebSocket frames

2. **Backend logging**
   ```python
   import logging
   logger = logging.getLogger(__name__)

   # In ConnectionManager methods:
   logger.info(f"Player connected to game {game_id}")
   logger.info(f"Broadcasting to {len(connections)} clients")
   ```

3. **Common issues**
   - **Connection closes immediately**: Check `player_id` query param is being passed
   - **No messages received**: Verify `broadcast()` is being called in routes
   - **CORS errors**: WebSocket URL must use `ws://` not `http://`
   - **JSON parse errors**: Both sides must send valid JSON

---

## Checklist

Use this to track your progress:

- [ ] **Backend: ConnectionManager** (`services/websocket.py`)
  - [ ] `connect()` method
  - [ ] `disconnect()` method
  - [ ] `broadcast()` method

- [ ] **Backend: WebSocket endpoint** (`api/routes.py`)
  - [ ] Basic `/ws/game/{game_id}` endpoint
  - [ ] Broadcast on player join
  - [ ] Broadcast on game start
  - [ ] Broadcast on submission
  - [ ] Broadcast on winner selection
  - [ ] Broadcast on round advance

- [ ] **Frontend: WebSocket service** (`services/websocket.ts`)
  - [ ] `connect()` method
  - [ ] `onMessage()` handler
  - [ ] `disconnect()` method

- [ ] **Frontend: Store integration** (`stores/game.ts`)
  - [ ] Add WebSocket instance
  - [ ] Connect after create/join
  - [ ] Disconnect on leave

- [ ] **Frontend: Remove polling**
  - [ ] LobbyView.vue
  - [ ] GameView.vue

- [ ] **Testing**
  - [ ] Manual: Connection appears in DevTools
  - [ ] Manual: Multi-client updates work
  - [ ] Automated: `test_websocket.py` passes

---

## Quick Reference

| File | Purpose |
|------|---------|
| `backend/app/services/websocket.py` | ConnectionManager class |
| `backend/app/api/routes.py` | WebSocket endpoint + broadcast calls |
| `frontend/src/services/websocket.ts` | GameWebSocket class |
| `frontend/src/stores/game.ts` | Store integration |
| `frontend/src/views/LobbyView.vue` | Remove polling |
| `frontend/src/views/GameView.vue` | Remove polling |
| `backend/tests/test_websocket.py` | Backend WebSocket tests |

Good luck! Take it one part at a time and test frequently.
