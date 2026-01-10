# Frontend Fundamentals: TypeScript + Vue + Vite

This tutorial teaches TypeScript and Vue 3 (Composition API) using your Ransom Notes game as a practical example.

## Table of Contents
1. [TypeScript Basics](#typescript-basics)
2. [Vue 3 Composition API](#vue-3-composition-api)
3. [Pinia State Management](#pinia-state-management)
4. [Vue Router](#vue-router)
5. [Project Structure](#project-structure)

---

## TypeScript Basics

### What is TypeScript?

TypeScript = JavaScript + Type System

It catches errors **before** your code runs:

```typescript
// JavaScript - crashes at runtime 💥
function greet(name) {
  return "Hello " + name.toUpperCase()
}
greet(123)  // Runtime error: name.toUpperCase is not a function

// TypeScript - error caught immediately ✅
function greet(name: string) {
  return "Hello " + name.toUpperCase()
}
greet(123)  // Compile error: Argument of type 'number' is not assignable to parameter of type 'string'
```

### 1. Basic Types

Let's look at your game code in `frontend/src/types/game.ts`:

```typescript
// Primitive types
const gameId: string = "abc123"
const playerCount: number = 5
const isHost: boolean = true
const tiles: string[] = ["cat", "dog", "run"]  // Array of strings

// Special types
let something: any = "anything"  // Avoid! Disables type checking
let nothing: null = null
let notSet: undefined = undefined
```

**Key Concept**: The `: type` syntax tells TypeScript what kind of value a variable can hold.

### 2. Interfaces - Defining Object Shapes

Open `frontend/src/types/game.ts` and look at `PlayerInfo`:

```typescript
export interface PlayerInfo {
  id: string
  nickname: string
  score: number
  is_host: boolean
  is_connected: boolean
}
```

**What this means**: Any object labeled as `PlayerInfo` MUST have these exact properties with these exact types.

```typescript
// ✅ Valid
const player: PlayerInfo = {
  id: "123",
  nickname: "Alice",
  score: 5,
  is_host: true,
  is_connected: true
}

// ❌ Error: missing 'score'
const badPlayer: PlayerInfo = {
  id: "123",
  nickname: "Bob",
  is_host: false,
  is_connected: true
}

// ❌ Error: 'score' should be number, not string
const wrongType: PlayerInfo = {
  id: "123",
  nickname: "Charlie",
  score: "five",  // Wrong type!
  is_host: false,
  is_connected: true
}
```

**Why interfaces?** They create a "contract" - if you expect a `PlayerInfo`, you can safely access `player.nickname` knowing it exists and is a string.

### 3. Type Aliases - Union Types

Look at `GamePhase` in `types/game.ts`:

```typescript
export type GamePhase = 'lobby' | 'playing' | 'judging' | 'round_end' | 'game_over'
```

The `|` means "or". A `GamePhase` can be **one of these specific strings, and nothing else**.

```typescript
let phase: GamePhase

phase = 'lobby'      // ✅ OK
phase = 'playing'    // ✅ OK
phase = 'waiting'    // ❌ Error: "waiting" is not a valid GamePhase
```

**Why?** This prevents typos and invalid states. You can't accidentally set `phase = 'loby'` (missing 'b').

### 4. Optional Properties

In your `GameConfig`:

```typescript
export interface GameConfig {
  max_players: number
  rounds_to_win: number
  time_limit?: number  // ← The ? makes this optional
}
```

The `?` means "this property might not exist":

```typescript
// Both valid:
const config1: GameConfig = {
  max_players: 8,
  rounds_to_win: 5
}

const config2: GameConfig = {
  max_players: 8,
  rounds_to_win: 5,
  time_limit: 60
}

// When accessing optional properties, check if they exist:
if (config1.time_limit) {
  console.log("Time limit:", config1.time_limit)  // Might not run
}
```

### 5. Generics - Reusable Types

Generics let you write flexible, reusable code. Look at Vue's `ref`:

```typescript
import { ref } from 'vue'

// ref is a generic function: ref<T>(value: T)
// The <T> is a placeholder for any type

const name = ref<string>("Alice")      // ref<string>
const count = ref<number>(0)           // ref<number>
const players = ref<PlayerInfo[]>([])  // ref<PlayerInfo[]>

// TypeScript knows the types!
name.value.toUpperCase()    // ✅ OK - string has toUpperCase
count.value.toUpperCase()   // ❌ Error - number doesn't have toUpperCase
```

**Generic Response Pattern** (common in APIs):

```typescript
interface ApiResponse<T> {
  success: boolean
  data: T  // T can be anything!
}

// Now we can reuse this for different data types:
const gameResponse: ApiResponse<GameCreatedResponse> = {
  success: true,
  data: { game_id: "123", player_id: "456", invite_code: "ABCD" }
}

const playerResponse: ApiResponse<PlayerInfo> = {
  success: true,
  data: { id: "789", nickname: "Bob", score: 0, is_host: false, is_connected: true }
}
```

### 6. Function Types

Look at `frontend/src/api/game.ts`:

```typescript
// This function signature tells us:
// - Takes two strings (hostNickname)
// - Returns a Promise that resolves to GameCreatedResponse
export async function createGame(hostNickname: string): Promise<GameCreatedResponse> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host_nickname: hostNickname }),
  })

  if (!response.ok) {
    throw new Error('Failed to create game')
  }

  return response.json()  // TypeScript knows this returns GameCreatedResponse
}
```

**Type Inference**: Sometimes TypeScript can figure out types automatically:

```typescript
// Explicit type
const result: GameCreatedResponse = await createGame("Alice")

// Inferred type - TypeScript knows createGame returns Promise<GameCreatedResponse>
const result = await createGame("Alice")  // Same thing!
```

### 7. Null and Undefined Handling

TypeScript helps you handle missing values safely:

```typescript
// In your store (stores/game.ts):
const gameId = ref<string | null>(null)  // Can be string OR null

// Later in code:
if (gameId.value) {
  // TypeScript knows gameId.value is a string here (not null)
  console.log(gameId.value.toUpperCase())  // ✅ Safe
}

// Without the check:
console.log(gameId.value.toUpperCase())  // ❌ Error: Object is possibly 'null'
```

---

## Vue 3 Composition API

Vue 3 uses the **Composition API** - a way to organize component logic using functions.

### The Old Way (Options API)

```javascript
export default {
  data() {
    return {
      count: 0,
      name: "Alice"
    }
  },
  computed: {
    greeting() {
      return `Hello ${this.name}!`
    }
  },
  methods: {
    increment() {
      this.count++
    }
  }
}
```

### The New Way (Composition API)

```typescript
import { ref, computed } from 'vue'

export default {
  setup() {
    // State
    const count = ref(0)
    const name = ref("Alice")

    // Computed
    const greeting = computed(() => `Hello ${name.value}!`)

    // Methods
    function increment() {
      count.value++
    }

    // Expose to template
    return { count, name, greeting, increment }
  }
}
```

**Or with `<script setup>` (what you're using):**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'

const count = ref(0)
const name = ref("Alice")
const greeting = computed(() => `Hello ${name.value}!`)

function increment() {
  count.value++
}
// Everything is automatically exposed to template!
</script>
```

### Core Concepts

#### 1. `ref()` - Reactive Values

`ref()` makes a value **reactive** - when it changes, Vue updates the UI automatically.

```typescript
import { ref } from 'vue'

const count = ref(0)

// Access/modify the value with .value
console.log(count.value)  // 0
count.value++             // 1
count.value = 10          // 10

// In templates, .value is automatic:
// <template>
//   <p>Count: {{ count }}</p>  <!-- No .value needed! -->
// </template>
```

**In your game** (`stores/game.ts`):

```typescript
const gameId = ref<string | null>(null)
const players = ref<PlayerInfo[]>([])
const isLoading = ref(false)

// When these change, any component using them re-renders
gameId.value = "abc123"  // UI updates!
players.value.push(newPlayer)  // UI updates!
```

#### 2. `computed()` - Derived State

`computed()` creates values that automatically update when their dependencies change:

```typescript
import { ref, computed } from 'vue'

const players = ref<PlayerInfo[]>([
  { id: '1', nickname: 'Alice', score: 5, is_host: true, is_connected: true },
  { id: '2', nickname: 'Bob', score: 3, is_host: false, is_connected: true }
])

// This automatically updates when players changes
const playerCount = computed(() => players.value.length)

console.log(playerCount.value)  // 2

players.value.push({
  id: '3',
  nickname: 'Charlie',
  score: 0,
  is_host: false,
  is_connected: true
})

console.log(playerCount.value)  // 3 (automatically updated!)
```

**In your game store**:

```typescript
const gameId = ref<string | null>(null)
const playerId = ref<string | null>(null)
const players = ref<PlayerInfo[]>([])

// Computed values
const isInGame = computed(() => gameId.value !== null)
const currentPlayer = computed(() =>
  players.value.find(p => p.id === playerId.value)
)
const isHost = computed(() => currentPlayer.value?.is_host ?? false)
```

**Why computed vs just a function?**

```typescript
// ❌ Function (recalculates every time)
function getPlayerCount() {
  return players.value.length
}

// ✅ Computed (caches result, only recalculates when players changes)
const playerCount = computed(() => players.value.length)
```

Computed values are **cached** and only recalculate when dependencies change. More efficient!

#### 3. `reactive()` - Reactive Objects

An alternative to `ref()` for objects:

```typescript
import { reactive } from 'vue'

// With ref (need .value)
const state = ref({
  count: 0,
  name: "Alice"
})
state.value.count++  // Need .value

// With reactive (no .value)
const state = reactive({
  count: 0,
  name: "Alice"
})
state.count++  // No .value needed!
```

**When to use which?**
- `ref()`: Primitives (string, number, boolean) and when you want consistent `.value` syntax
- `reactive()`: Complex objects where you don't want `.value`

Most people stick with `ref()` for consistency.

#### 4. Template Syntax

In your `.vue` files:

```vue
<template>
  <!-- Interpolation -->
  <p>Game ID: {{ gameId }}</p>

  <!-- Binding attributes -->
  <button :disabled="isLoading">Join</button>
  <!-- Same as v-bind:disabled="isLoading" -->

  <!-- Event handling -->
  <button @click="handleJoin">Join Game</button>
  <!-- Same as v-on:click="handleJoin" -->

  <!-- Conditional rendering -->
  <div v-if="isInGame">You're in a game!</div>
  <div v-else>Not in a game</div>

  <!-- List rendering -->
  <div v-for="player in players" :key="player.id">
    {{ player.nickname }} - Score: {{ player.score }}
  </div>

  <!-- Two-way binding -->
  <input v-model="nickname" placeholder="Enter nickname">
  <!-- Automatically syncs input value with nickname ref -->
</template>

<script setup lang="ts">
import { ref } from 'vue'

const gameId = ref<string | null>(null)
const isLoading = ref(false)
const isInGame = computed(() => gameId.value !== null)
const players = ref<PlayerInfo[]>([])
const nickname = ref('')

function handleJoin() {
  // Join game logic
}
</script>
```

---

## Pinia State Management

Pinia is Vue's official state management library (replaces Vuex). Think of it as a "global store" for your app's data.

### Why Pinia?

Without Pinia, you'd need to pass data through many component layers:

```
App
 └─ GameView
     └─ Lobby
         └─ PlayerList
             └─ Player  (needs game data from App!)
```

With Pinia, any component can access the store directly:

```typescript
// In ANY component
const gameStore = useGameStore()
console.log(gameStore.players)  // Direct access!
```

### Anatomy of a Store

Look at `frontend/src/stores/game.ts`:

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useGameStore = defineStore('game', () => {
  // 1. STATE - Reactive data
  const gameId = ref<string | null>(null)
  const players = ref<PlayerInfo[]>([])
  const isLoading = ref(false)

  // 2. GETTERS - Computed values (derived state)
  const isInGame = computed(() => gameId.value !== null)
  const playerCount = computed(() => players.value.length)

  // 3. ACTIONS - Functions that modify state
  async function createGame(nickname: string) {
    isLoading.value = true
    try {
      const response = await api.createGame(nickname)
      gameId.value = response.game_id
      playerId.value = response.player_id
      // ... update other state
    } finally {
      isLoading.value = false
    }
  }

  // 4. RETURN - Expose what components can use
  return {
    // State
    gameId,
    players,
    isLoading,
    // Getters
    isInGame,
    playerCount,
    // Actions
    createGame
  }
})
```

### Using the Store in Components

```vue
<script setup lang="ts">
import { useGameStore } from '@/stores/game'

// Get store instance
const gameStore = useGameStore()

// Access state/getters directly
console.log(gameStore.gameId)
console.log(gameStore.isInGame)

// Call actions
async function join() {
  await gameStore.createGame("Alice")
}
</script>

<template>
  <!-- Use in template -->
  <div v-if="gameStore.isLoading">Loading...</div>
  <div v-else>
    <p>Players: {{ gameStore.playerCount }}</p>
    <button @click="join">Create Game</button>
  </div>
</template>
```

### Key Store Patterns

#### 1. Async Actions

```typescript
async function joinGame(code: string, nickname: string) {
  isLoading.value = true
  error.value = null  // Clear previous errors

  try {
    const response = await api.joinGame(code, nickname)
    // Update state on success
    gameId.value = response.game_id
    playerId.value = response.player_id
  } catch (e) {
    // Handle errors
    error.value = e instanceof Error ? e.message : 'Unknown error'
    throw e  // Re-throw so component can handle it too
  } finally {
    // Always runs (success or error)
    isLoading.value = false
  }
}
```

#### 2. State Reset

```typescript
function leaveGame() {
  // Reset all state to initial values
  gameId.value = null
  playerId.value = null
  players.value = []
  error.value = null
}
```

#### 3. Optimistic Updates

```typescript
function addPlayer(player: PlayerInfo) {
  // Update UI immediately (optimistic)
  players.value.push(player)

  // Then sync with backend
  api.updatePlayers(players.value).catch(() => {
    // Revert on error
    players.value = players.value.filter(p => p.id !== player.id)
  })
}
```

---

## Vue Router

Vue Router manages navigation between pages (views) in your single-page app.

### Basic Setup

Look at `frontend/src/router/index.ts`:

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
      path: '/lobby',
      name: 'lobby',
      component: () => import('../views/LobbyView.vue')  // Lazy loaded
    }
  ]
})

export default router
```

### Routes Explained

```typescript
{
  path: '/lobby',        // URL path
  name: 'lobby',        // Named route (for programmatic navigation)
  component: LobbyView  // Which component to render
}
```

### Navigation

#### In Templates

```vue
<template>
  <!-- Declarative navigation -->
  <router-link to="/">Home</router-link>
  <router-link to="/lobby">Lobby</router-link>

  <!-- Named routes -->
  <router-link :to="{ name: 'lobby' }">Lobby</router-link>

  <!-- Where the matched component renders -->
  <router-view />
</template>
```

#### In JavaScript

```typescript
import { useRouter } from 'vue-router'

const router = useRouter()

// Navigate to a path
router.push('/lobby')

// Navigate to a named route
router.push({ name: 'lobby' })

// Navigate with parameters
router.push({
  name: 'game',
  params: { id: '123' },
  query: { player: 'Alice' }  // ?player=Alice
})

// Go back
router.back()
```

### Route Parameters

```typescript
// Route definition
{
  path: '/game/:id',
  name: 'game',
  component: GameView
}

// In component
import { useRoute } from 'vue-router'

const route = useRoute()
console.log(route.params.id)  // Access :id parameter
```

---

## Project Structure

Let's walk through your frontend structure:

```
frontend/src/
├── api/              # API calls to backend
│   └── game.ts       # Game-related API functions
├── assets/           # Static assets (CSS, images)
├── components/       # Reusable Vue components
├── router/           # Vue Router configuration
├── stores/           # Pinia stores (global state)
│   └── game.ts       # Game state management
├── types/            # TypeScript type definitions
│   └── game.ts       # Game-related types/interfaces
├── views/            # Page components (routes)
│   ├── HomeView.vue
│   └── LobbyView.vue
├── App.vue           # Root component
└── main.ts           # App entry point
```

### Key Files Explained

#### `main.ts` - Entry Point

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)  // Create Vue app

app.use(createPinia())  // Add Pinia (state management)
app.use(router)         // Add Vue Router (routing)

app.mount('#app')       // Mount to DOM
```

#### `types/game.ts` - TypeScript Definitions

All your interfaces and types for type safety.

#### `api/game.ts` - API Layer

Functions that talk to your backend. Keeps API logic separate from components.

#### `stores/game.ts` - State Management

Global state that any component can access.

#### `views/` - Page Components

Components that are rendered by routes (full pages).

#### `components/` - Reusable Components

Smaller pieces used within views (buttons, cards, forms, etc.).

---

## Putting It All Together

Let's trace through creating a game:

### 1. User clicks "Create Game" button

```vue
<!-- HomeView.vue -->
<template>
  <input v-model="nickname" placeholder="Your nickname">
  <button @click="handleCreate">Create Game</button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'

const nickname = ref('')
const router = useRouter()
const gameStore = useGameStore()

async function handleCreate() {
  try {
    await gameStore.createGame(nickname.value)
    router.push({ name: 'lobby' })  // Navigate to lobby
  } catch (error) {
    alert('Failed to create game')
  }
}
</script>
```

### 2. Store calls API

```typescript
// stores/game.ts
async function createGame(nickname: string) {
  isLoading.value = true
  try {
    const response = await api.createGame(nickname)  // ← Calls API function
    gameId.value = response.game_id
    playerId.value = response.player_id
    // ... update state
  } finally {
    isLoading.value = false
  }
}
```

### 3. API function makes HTTP request

```typescript
// api/game.ts
export async function createGame(hostNickname: string): Promise<GameCreatedResponse> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host_nickname: hostNickname }),
  })

  if (!response.ok) {
    throw new Error('Failed to create game')
  }

  return response.json()  // TypeScript knows this is GameCreatedResponse
}
```

### 4. Backend responds, state updates

```typescript
// stores/game.ts (continued)
gameId.value = response.game_id     // State updates
playerId.value = response.player_id
players.value = [response.player]   // Reactive!

// Any component watching these values automatically re-renders!
```

### 5. Router navigates to lobby

```typescript
router.push({ name: 'lobby' })  // Changes URL and renders LobbyView
```

### 6. Lobby displays state

```vue
<!-- LobbyView.vue -->
<template>
  <div>
    <h1>Game Lobby</h1>
    <p>Invite Code: {{ gameStore.inviteCode }}</p>
    <p>Players: {{ gameStore.playerCount }}</p>

    <div v-for="player in gameStore.players" :key="player.id">
      {{ player.nickname }}
      <span v-if="player.is_host">(Host)</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '@/stores/game'

const gameStore = useGameStore()
// Automatically reactive! When store updates, template updates.
</script>
```

---

## Next Steps

1. **Explore the code**: Open files in PyCharm and trace through the flow
2. **Make changes**: Try adding a new field to `PlayerInfo` and see TypeScript errors
3. **Add features**: Create a new computed property in the store
4. **Debug**: Use Vue DevTools browser extension to inspect state

Want to dive deeper into any of these concepts? Let me know!
