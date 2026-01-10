# Learning WebSockets, TypeScript, and Vue Through Ransom Notes

This guide will teach you WebSockets, TypeScript, and Vue.js concepts using your actual game code.

## Table of Contents
1. [WebSockets Overview](#websockets-overview)
2. [TypeScript Fundamentals](#typescript-fundamentals)
3. [Vue 3 Composition API](#vue-3-composition-api)
4. [Implementing Real-time Features](#implementing-real-time-features)

---

## WebSockets Overview

### What Are WebSockets?

WebSockets provide **full-duplex** communication between a client and server. Unlike HTTP:

- **HTTP**: Client requests → Server responds → Connection closes
- **WebSocket**: Client ↔ Server maintain an open connection for bidirectional communication

### Why WebSockets for Ransom Notes?

Your game needs real-time updates:
- When a player joins, all players should see them instantly
- When the host starts the game, everyone transitions together
- When players submit answers, the judge sees them immediately
- When a winner is chosen, scores update for everyone

### WebSocket Lifecycle

```
1. Handshake (HTTP Upgrade)
   Client: "Hey, let's upgrade to WebSocket!"
   Server: "Sure! Connection established."

2. Open Connection
   - Both sides can send messages anytime
   - Messages are events (not request/response)

3. Message Exchange
   Client → Server: "I submitted my answer"
   Server → All Clients: "Player X submitted"

4. Close
   Either side can close the connection
```

### WebSocket Events in FastAPI

```python
@router.websocket("/ws/game/{game_id}")
async def game_websocket(
    websocket: WebSocket,
    game_id: str,
    player_id: str  # Usually from query params
):
    # 1. Accept the connection
    await websocket.accept()

    try:
        # 2. Listen for messages
        while True:
            data = await websocket.receive_json()
            # Process the message

            # 3. Send messages back
            await websocket.send_json({"type": "update", "data": ...})

    except WebSocketDisconnect:
        # 4. Handle disconnection
        print(f"Player {player_id} disconnected")
```

---

## TypeScript Fundamentals

### Why TypeScript?

TypeScript adds **type safety** to JavaScript. It catches errors before runtime:

```typescript
// JavaScript - Error at runtime! 💥
const player = { name: "Alice" }
console.log(player.score)  // undefined - oops!

// TypeScript - Error at compile time! ✅
interface Player {
  name: string
  score: number  // We know this is required
}
const player: Player = { name: "Alice" }  // Error: missing 'score'
```

### Core Concepts in Your Game

#### 1. **Primitive Types**

```typescript
// In your game
const gameId: string = "abc-123"
const playerCount: number = 4
const isHost: boolean = true
const tiles: string[] = ["cat", "dog", "house"]
```

#### 2. **Interfaces** (Shape of Objects)

Look at `frontend/src/types/game.ts`:

```typescript
export interface PlayerInfo {
  id: string
  nickname: string
  score: number
  is_host: boolean
  is_connected: boolean
}
```

This says: "A PlayerInfo must have these exact properties with these types."

#### 3. **Type Aliases** (Union Types)

```typescript
export type GamePhase = 'lobby' | 'playing' | 'judging' | 'round_end' | 'game_over'
```

This means: "GamePhase can ONLY be one of these five string values."

```typescript
let phase: GamePhase = 'lobby'  // ✅ OK
phase = 'waiting'  // ❌ Error: "waiting" is not a valid GamePhase
```

#### 4. **Generics** (Reusable Types)

```typescript
// A generic response wrapper
interface ApiResponse<T> {
  success: boolean
  data: T  // T can be any type!
}

// Now we can use it with different data types
const gameResponse: ApiResponse<GameCreatedResponse> = {
  success: true,
  data: { game_id: "123", player_id: "456", ... }
}

const playerResponse: ApiResponse<PlayerInfo> = {
  success: true,
  data: { id: "789", nickname: "Bob", ... }
}
```

#### 5. **Optional Properties**

```typescript
interface GameConfig {
  max_players: number
  rounds_to_win: number
  time_limit?: number  // ? means optional
}

// Both valid:
const config1: GameConfig = { max_players: 8, rounds_to_win: 5 }
const config2: GameConfig = { max_players: 8, rounds_to_win: 5, time_limit: 60 }
```

#### 6. **Function Types**

```typescript
// Type for a function that takes a string and returns a Promise of PlayerInfo
type JoinGameFn = (inviteCode: string, nickname: string) => Promise<GameJoinedResponse>

// Using it:
const joinGame: JoinGameFn = async (code, nick) => {
  const response = await fetch(...)
  return response.json()
}
```

---

## Vue 3 Composition API

### Reactivity System

Vue's magic is **reactivity** - when data changes, the UI updates automatically.

#### `ref()` - Reactive Primitive Values

```typescript
import { ref } from 'vue'

// Create a reactive value
const count = ref(0)

// Access value with .value
console.log(count.value)  // 0

// Changing it triggers UI updates
count.value++  // UI re-renders!
```

In your game store (`stores/game.ts`):

```typescript
const gameId = ref<string | null>(null)  // Generic: ref of string or null
const players = ref<PlayerInfo[]>([])     // ref of PlayerInfo array
```

#### `computed()` - Derived State

```typescript
import { computed } from 'vue'

const players = ref<PlayerInfo[]>([
  { id: '1', nickname: 'Alice', score: 5, is_host: true, is_connected: true },
  { id: '2', nickname: 'Bob', score: 3, is_host: false, is_connected: true }
])

// Computed value automatically updates when players changes
const playerCount = computed(() => players.value.length)

console.log(playerCount.value)  // 2

players.value.push({ id: '3', nickname: 'Charlie', ... })
console.log(playerCount.value)  // 3 - automatically updated!
```

#### Pinia Stores (State Management)

Your game store is the "single source of truth" for game state:

```typescript
export const useGameStore = defineStore('game', () => {
  // State (reactive data)
  const gameId = ref<string | null>(null)
  const players = ref<PlayerInfo[]>([])

  // Getters (computed values)
  const isInGame = computed(() => gameId.value !== null)

  // Actions (functions that modify state)
  async function createGame(nickname: string) {
    const response = await api.createGame(nickname)
    gameId.value = response.game_id  // Update state
  }

  // Return everything you want to expose
  return { gameId, players, isInGame, createGame }
})
```

Using it in a component:

```typescript
import { useGameStore } from '@/stores/game'

const gameStore = useGameStore()

// Access state
console.log(gameStore.gameId)

// Call actions
await gameStore.createGame('Alice')
```

---

## Implementing Real-time Features

Now let's add WebSockets to make your game real-time! We'll build:

1. **Backend**: WebSocket connection manager
2. **Frontend**: WebSocket service (TypeScript)
3. **Store Integration**: Update Vue store from WebSocket events
4. **UI**: Real-time lobby updates

### Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│                                                  │
│  ┌────────────┐         ┌─────────────────┐    │
│  │ Component  │ ◄──────►│  Pinia Store    │    │
│  │ (Vue)      │         │  (game.ts)      │    │
│  └────────────┘         └────────┬────────┘    │
│                                   │              │
│                         ┌─────────▼────────┐    │
│                         │ WebSocket Service│    │
│                         │ (TypeScript)     │    │
│                         └─────────┬────────┘    │
└─────────────────────────────────┬─┴──────────────┘
                                  │
                    WebSocket Connection (ws://)
                                  │
┌─────────────────────────────────┴─┬─────────────┐
│                  Backend            │            │
│                                     │            │
│  ┌──────────────────────────────────▼─────────┐ │
│  │     WebSocket Endpoint (FastAPI)           │ │
│  │     /ws/game/{game_id}                     │ │
│  └──────────────────┬─────────────────────────┘ │
│                     │                            │
│  ┌──────────────────▼─────────────────────────┐ │
│  │  Connection Manager                        │ │
│  │  - Tracks active connections               │ │
│  │  - Broadcasts to all players in a game     │ │
│  └──────────────────┬─────────────────────────┘ │
│                     │                            │
│  ┌──────────────────▼─────────────────────────┐ │
│  │        Game Service                        │ │
│  │        (Existing game logic)               │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

See the implementation files for details!
