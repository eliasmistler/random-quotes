# Code Walkthrough: How Your Ransom Notes Game Works

This document walks through your actual code to show how TypeScript, Vue, and Vite work together.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                             │
│  ┌────────────────────────────────────────────────┐    │
│  │           Vue Application                       │    │
│  │                                                 │    │
│  │  ┌──────────┐    ┌──────────┐   ┌──────────┐ │    │
│  │  │  Views   │───►│  Stores  │◄──│   API    │ │    │
│  │  │ (.vue)   │    │ (Pinia)  │   │  Layer   │ │    │
│  │  └──────────┘    └──────────┘   └─────┬────┘ │    │
│  │       ▲              ▲                  │      │    │
│  │       │              │                  │      │    │
│  │  ┌────┴──────────────┴────┐            │      │    │
│  │  │     Components         │            │      │    │
│  │  └────────────────────────┘            │      │    │
│  └────────────────────────────────────────┼──────┘    │
└───────────────────────────────────────────┼───────────┘
                                            │
                                    HTTP Requests
                                            │
┌───────────────────────────────────────────┼───────────┐
│                   FastAPI Backend         ▼           │
│                                                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │  Routes  │───►│ Services │───►│  Models  │       │
│  │  (API)   │    │ (Logic)  │    │  (Data)  │       │
│  └──────────┘    └──────────┘    └──────────┘       │
└────────────────────────────────────────────────────────┘
```

---

## 1. Application Startup

### `main.ts` - The Entry Point

```typescript
import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
```

**What happens here:**

1. **`createApp(App)`** - Creates the Vue application instance
   - `App` is your root component (App.vue)

2. **`createPinia()`** - Sets up Pinia for state management
   - This allows `useGameStore()` to work in any component

3. **`app.use(router)`** - Adds Vue Router
   - Enables navigation between pages

4. **`app.mount('#app')`** - Mounts the app to the DOM
   - Looks for `<div id="app">` in `index.html`
   - This is where your Vue app replaces the HTML

**The HTML file** (`index.html`):
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ransom Notes</title>
  </head>
  <body>
    <div id="app"></div> <!-- Vue mounts here -->
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

---

## 2. Type Definitions

### `types/game.ts` - The Contract

This file defines all the data shapes used in your app:

```typescript
export interface PlayerInfo {
  id: string
  nickname: string
  score: number
  is_host: boolean
  is_connected: boolean
}
```

**Why this matters:**
- When you write `player.nickname`, TypeScript knows it's a string
- If you type `player.nicknam` (typo), TypeScript catches it
- Auto-complete works everywhere

```typescript
export type GamePhase = 'lobby' | 'playing' | 'judging' | 'round_end' | 'game_over'
```

**This prevents bugs:**
```typescript
let phase: GamePhase = 'lobby'  // ✅
phase = 'loby'  // ❌ TypeScript error!
```

```typescript
export interface GameCreatedResponse {
  game_id: string
  invite_code: string
  player_id: string
  player: PlayerInfo
}
```

**API contract:**
- Your frontend expects this exact shape from the backend
- TypeScript ensures you use the data correctly

---

## 3. API Layer

### `api/game.ts` - Talking to the Backend

```typescript
const API_BASE = 'http://localhost:8000/api'

export async function createGame(hostNickname: string): Promise<GameCreatedResponse> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ host_nickname: hostNickname }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to create game')
  }

  return response.json()
}
```

**Breaking it down:**

1. **Function signature:**
   ```typescript
   async function createGame(hostNickname: string): Promise<GameCreatedResponse>
   ```
   - Takes a string (nickname)
   - Returns a Promise that resolves to `GameCreatedResponse`
   - TypeScript knows what data you'll get back

2. **Making the request:**
   ```typescript
   await fetch(`${API_BASE}/games`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ host_nickname: hostNickname })
   })
   ```
   - `fetch()` is the browser API for HTTP requests
   - `await` pauses until the request completes
   - Sends JSON data to your FastAPI backend

3. **Error handling:**
   ```typescript
   if (!response.ok) {
     const error = await response.json()
     throw new Error(error.detail?.error || 'Failed to create game')
   }
   ```
   - Checks if request succeeded (status 200-299)
   - Throws an error if it failed
   - The `?` is optional chaining (safe property access)

4. **Return the data:**
   ```typescript
   return response.json()
   ```
   - TypeScript knows this returns `GameCreatedResponse`
   - Your IDE will autocomplete the response properties

**Same pattern for other API calls:**
```typescript
export async function joinGame(inviteCode: string, nickname: string): Promise<GameJoinedResponse>
export async function getGameState(gameId: string, playerId: string): Promise<GameStateResponse>
```

---

## 4. State Management

### `stores/game.ts` - The Brain of Your App

This is where all game state lives. Let's break it down piece by piece:

#### Part 1: Setup and State

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { PlayerInfo, GamePhase } from '@/types/game'
import * as api from '@/api/game'

export const useGameStore = defineStore('game', () => {
  // State - reactive data
  const gameId = ref<string | null>(null)
  const playerId = ref<string | null>(null)
  const inviteCode = ref<string | null>(null)
  const phase = ref<GamePhase | null>(null)
  const players = ref<PlayerInfo[]>([])
  const myTiles = ref<string[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
```

**What's happening:**
- `defineStore('game', ...)` creates a Pinia store named 'game'
- Each `ref()` creates a reactive value
- `ref<string | null>` means "string or null" (union type)
- `ref<PlayerInfo[]>` means "array of PlayerInfo objects"

**Why refs?**
- When you change `gameId.value = "abc123"`, Vue automatically updates any component using it
- Magic reactivity! 🪄

#### Part 2: Computed Values (Getters)

```typescript
  const isInGame = computed(() => gameId.value !== null)
  const currentPlayer = computed(() => players.value.find((p) => p.id === playerId.value))
  const isHost = computed(() => currentPlayer.value?.is_host ?? false)
  const playerCount = computed(() => players.value.length)
```

**How computed works:**
- `computed()` creates a derived value
- It automatically recalculates when dependencies change
- Cached - only runs when needed

**Example:**
```typescript
// gameId changes
gameId.value = "abc123"

// isInGame automatically becomes true
// Any component displaying isInGame re-renders
```

**The `?.` operator:**
```typescript
currentPlayer.value?.is_host
// If currentPlayer is null/undefined, returns undefined
// Otherwise, returns is_host
// Prevents "Cannot read property 'is_host' of null" errors
```

**The `??` operator:**
```typescript
currentPlayer.value?.is_host ?? false
// If left side is null/undefined, use false
// Otherwise, use the left side value
```

#### Part 3: Actions (Methods)

```typescript
  async function createGame(nickname: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.createGame(nickname)
      gameId.value = response.game_id
      playerId.value = response.player_id
      inviteCode.value = response.invite_code
      phase.value = 'lobby'
      players.value = [
        {
          id: response.player.id,
          nickname: response.player.nickname,
          score: response.player.score,
          is_host: response.player.is_host,
          is_connected: response.player.is_connected,
        },
      ]
      myTiles.value = response.player.word_tiles
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }
```

**Flow of execution:**

1. **Set loading state:**
   ```typescript
   isLoading.value = true
   ```
   Components can show a spinner

2. **Clear previous errors:**
   ```typescript
   error.value = null
   ```

3. **Try to create game:**
   ```typescript
   const response = await api.createGame(nickname)
   ```
   Calls your API function, waits for response

4. **Update all state:**
   ```typescript
   gameId.value = response.game_id
   playerId.value = response.player_id
   // ... etc
   ```
   All reactive values update
   All components watching these update automatically

5. **Handle errors:**
   ```typescript
   catch (e) {
     error.value = e instanceof Error ? e.message : 'Unknown error'
     throw e  // Re-throw so component can handle it
   }
   ```

6. **Always clean up:**
   ```typescript
   finally {
     isLoading.value = false  // Runs whether success or error
   }
   ```

**Same pattern for joinGame:**
```typescript
  async function joinGame(code: string, nickname: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.joinGame(code, nickname)
      gameId.value = response.game_id
      playerId.value = response.player_id
      inviteCode.value = code.toUpperCase()
      await refreshGameState()  // Get full game state
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }
```

**Refresh game state:**
```typescript
  async function refreshGameState() {
    if (!gameId.value || !playerId.value) return

    try {
      const state = await api.getGameState(gameId.value, playerId.value)
      phase.value = state.phase
      players.value = state.players
      myTiles.value = state.my_tiles
      inviteCode.value = state.invite_code
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    }
  }
```

**Leave game (reset state):**
```typescript
  function leaveGame() {
    gameId.value = null
    playerId.value = null
    inviteCode.value = null
    phase.value = null
    players.value = []
    myTiles.value = []
    error.value = null
  }
```

#### Part 4: Return (Expose to Components)

```typescript
  return {
    // State
    gameId,
    playerId,
    inviteCode,
    phase,
    players,
    myTiles,
    isLoading,
    error,
    // Getters
    isInGame,
    currentPlayer,
    isHost,
    playerCount,
    // Actions
    createGame,
    joinGame,
    refreshGameState,
    leaveGame,
  }
})
```

**What you return is what components can access:**
```typescript
const gameStore = useGameStore()
console.log(gameStore.gameId)     // State
console.log(gameStore.isInGame)   // Getter
gameStore.createGame("Alice")     // Action
```

---

## 5. Views (Pages)

### `LobbyView.vue` - A Complete Component

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'

const router = useRouter()
const gameStore = useGameStore()

onMounted(() => {
  if (!gameStore.isInGame) {
    router.push({ name: 'home' })
  }
})

function handleLeave() {
  gameStore.leaveGame()
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="lobby">
    <h1>Game Lobby</h1>

    <div v-if="gameStore.isLoading">
      Loading...
    </div>

    <div v-else>
      <p>Invite Code: <strong>{{ gameStore.inviteCode }}</strong></p>
      <p>Players: {{ gameStore.playerCount }}</p>

      <div class="players">
        <div
          v-for="player in gameStore.players"
          :key="player.id"
          class="player"
        >
          {{ player.nickname }}
          <span v-if="player.is_host">(Host)</span>
        </div>
      </div>

      <button @click="handleLeave">Leave Game</button>
    </div>
  </div>
</template>
```

**Breaking it down:**

#### Script Section

```typescript
<script setup lang="ts">
```
- `setup` - using Composition API
- `lang="ts"` - TypeScript support

```typescript
import { onMounted } from 'vue'
```
- `onMounted` is a lifecycle hook
- Runs when component is added to the page

```typescript
const router = useRouter()
const gameStore = useGameStore()
```
- Get router instance (for navigation)
- Get game store instance (for state)

```typescript
onMounted(() => {
  if (!gameStore.isInGame) {
    router.push({ name: 'home' })
  }
})
```
- When component mounts, check if in a game
- If not, redirect to home page
- Route guard pattern!

```typescript
function handleLeave() {
  gameStore.leaveGame()  // Clear state
  router.push({ name: 'home' })  // Navigate
}
```
- Function called when button is clicked
- Actions → State changes → Navigation

#### Template Section

```vue
<div v-if="gameStore.isLoading">
  Loading...
</div>
```
- `v-if` - conditional rendering
- Only shows if `isLoading` is true
- When `isLoading` changes, Vue automatically updates

```vue
<p>Invite Code: <strong>{{ gameStore.inviteCode }}</strong></p>
```
- `{{ }}` - interpolation
- Displays the value of `inviteCode`
- Updates automatically when `inviteCode` changes

```vue
<div
  v-for="player in gameStore.players"
  :key="player.id"
  class="player"
>
```
- `v-for` - loop rendering
- Creates one div per player
- `:key` - required for efficient updates (tells Vue which item is which)

```vue
<span v-if="player.is_host">(Host)</span>
```
- Conditional rendering inside the loop
- Only shows for the host player

```vue
<button @click="handleLeave">Leave Game</button>
```
- `@click` - event listener (shorthand for `v-on:click`)
- Calls `handleLeave` when clicked

---

## 6. Router

### `router/index.ts` - Navigation

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue')
    },
    {
      path: '/lobby',
      name: 'lobby',
      component: () => import('../views/LobbyView.vue')
    }
  ]
})

export default router
```

**How routes work:**

```typescript
{
  path: '/lobby',        // URL: localhost:5173/lobby
  name: 'lobby',        // Reference name
  component: LobbyView  // Which component to render
}
```

**Lazy loading:**
```typescript
component: () => import('../views/LobbyView.vue')
```
- Only loads the component when needed
- Smaller initial bundle size
- Faster app startup

**Navigation:**
```typescript
// In a component
router.push('/lobby')           // Navigate to path
router.push({ name: 'lobby' })  // Navigate to named route
router.back()                   // Go back
```

---

## 7. Complete User Flow

Let's trace a complete action from button click to UI update:

### Creating a Game

1. **User types nickname and clicks "Create Game"**

2. **Component handler runs** (HomeView.vue):
   ```vue
   <script setup>
   async function handleCreate() {
     try {
       await gameStore.createGame(nickname.value)
       router.push({ name: 'lobby' })
     } catch (error) {
       alert('Failed to create game')
     }
   }
   </script>

   <template>
     <button @click="handleCreate">Create</button>
   </template>
   ```

3. **Store action runs** (stores/game.ts):
   ```typescript
   async function createGame(nickname: string) {
     isLoading.value = true  // ← UI shows loading spinner

     const response = await api.createGame(nickname)  // ← API call

     gameId.value = response.game_id  // ← State updates
     playerId.value = response.player_id
     // ... more updates

     isLoading.value = false  // ← UI hides spinner
   }
   ```

4. **API function calls backend** (api/game.ts):
   ```typescript
   export async function createGame(hostNickname: string) {
     const response = await fetch('http://localhost:8000/api/games', {
       method: 'POST',
       body: JSON.stringify({ host_nickname: hostNickname })
     })
     return response.json()  // ← Returns GameCreatedResponse
   }
   ```

5. **Backend processes request** (Python FastAPI):
   ```python
   @router.post("/games")
   def create_new_game(request: CreateGameRequest):
       game, host = create_game(host_nickname=request.host_nickname)
       return GameCreatedResponse(game_id=game.id, ...)
   ```

6. **Response flows back:**
   - Backend → API function → Store action → Component

7. **State updates trigger reactivity:**
   ```typescript
   gameId.value = "abc123"
   ```
   - Any component watching `gameId` re-renders
   - Computed values recalculate
   - UI updates automatically ✨

8. **Router navigates:**
   ```typescript
   router.push({ name: 'lobby' })
   ```
   - URL changes to `/lobby`
   - LobbyView component mounts
   - LobbyView accesses store and displays game data

**The complete flow:**
```
User Input
   ↓
Component Handler
   ↓
Store Action
   ↓
API Function
   ↓
HTTP Request → Backend → HTTP Response
   ↓
Update Store State
   ↓
Vue Reactivity System
   ↓
Components Re-render
   ↓
User Sees Updated UI
```

---

## 8. TypeScript in Action

### Type Safety Throughout

**API defines return type:**
```typescript
function createGame(nickname: string): Promise<GameCreatedResponse>
```

**Store uses that type:**
```typescript
const response = await api.createGame(nickname)
// TypeScript knows: response is GameCreatedResponse
```

**Can safely access properties:**
```typescript
gameId.value = response.game_id  // ✅ TypeScript knows this exists
playerId.value = response.player_id  // ✅
```

**Error if you typo:**
```typescript
gameId.value = response.gameId  // ❌ Property 'gameId' does not exist
```

**Component gets type checking:**
```typescript
const gameStore = useGameStore()
console.log(gameStore.gameId)  // ✅ TypeScript knows this exists
console.log(gameStore.gameid)  // ❌ Property 'gameid' does not exist
```

### Generics Example

```typescript
// ref is generic
const gameId = ref<string | null>(null)
// TypeScript knows gameId.value is string | null

// Can't assign wrong type
gameId.value = 123  // ❌ Type 'number' is not assignable to type 'string | null'
gameId.value = "abc"  // ✅
gameId.value = null  // ✅
```

---

## Summary: How It All Connects

```
┌────────── Component (.vue file) ──────────┐
│                                            │
│  <script setup>                            │
│    const gameStore = useGameStore() ◄──┐  │
│                                         │  │
│    function handleClick() {             │  │
│      gameStore.createGame("Alice") ──┐  │  │
│    }                                  │  │  │
│  </script>                            │  │  │
│                                       │  │  │
│  <template>                           │  │  │
│    {{ gameStore.players }} ◄──────────┼──┘  │
│  </template>                          │     │
└───────────────────────────────────────┼─────┘
                                        │
                    ┌───────────────────┘
                    ▼
┌────────── Store (Pinia) ──────────────┐
│                                        │
│  const players = ref([])  ◄────┐      │
│                                 │      │
│  function createGame() {        │      │
│    api.createGame() ──┐         │      │
│    players.value = ... ─────────┘      │
│  }                    │                │
└───────────────────────┼────────────────┘
                        │
        ┌───────────────┘
        ▼
┌────────── API Layer ──────────────────┐
│                                        │
│  async function createGame() {         │
│    fetch('/api/games') ──┐            │
│    return response.json() │            │
│  }                        │            │
└───────────────────────────┼────────────┘
                            │
            ┌───────────────┘
            ▼
    HTTP Request to Backend
```

Every piece has a purpose:
- **Types**: Define data shapes, prevent bugs
- **API Layer**: Centralize backend communication
- **Store**: Manage state, business logic
- **Components**: Display UI, handle user interaction
- **Router**: Navigate between pages

Together they create a type-safe, reactive, maintainable application!
