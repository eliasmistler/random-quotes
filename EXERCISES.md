# Frontend Exercises - Learning by Doing

These exercises use your actual Ransom Notes game code. Complete them in order to build your understanding.

## Exercise 1: TypeScript Type Safety

**Goal**: Practice working with TypeScript interfaces and types.

### Task 1.1: Add a new player property

1. Open `frontend/src/types/game.ts`
2. Add a new optional property to `PlayerInfo`:
   ```typescript
   avatar_color?: string  // Player's color in the UI
   ```
3. Notice how TypeScript now allows this property everywhere `PlayerInfo` is used
4. Try using it in the store or a component

### Task 1.2: Create a strict game phase type

Currently, your code might have phase as a string. Let's make it type-safe:

1. In `frontend/src/types/game.ts`, verify that `GamePhase` is a union type:
   ```typescript
   export type GamePhase = 'lobby' | 'playing' | 'judging' | 'round_end' | 'game_over'
   ```
2. Try to assign an invalid phase in your store:
   ```typescript
   phase.value = 'invalid'  // Should give a TypeScript error!
   ```
3. Notice how TypeScript prevents bugs before runtime

### Task 1.3: Add type safety to API calls

Look at `frontend/src/api/game.ts`. Let's add error handling with types:

1. Create an error type:
   ```typescript
   interface ApiError {
     error: string
     code: string
   }
   ```
2. Update `createGame` to use it:
   ```typescript
   if (!response.ok) {
     const error: ApiError = await response.json()
     throw new Error(error.error || 'Failed to create game')
   }
   ```

**Learning**: TypeScript helps you understand data shapes and prevents mistakes.

---

## Exercise 2: Vue Reactivity

**Goal**: Understand how Vue's reactivity system works.

### Task 2.1: Add a timer to the lobby

1. Open `frontend/src/stores/game.ts`
2. Add a new ref for elapsed time:
   ```typescript
   const lobbyTimer = ref(0)  // seconds in lobby
   ```
3. Create an action to increment it:
   ```typescript
   function startLobbyTimer() {
     setInterval(() => {
       lobbyTimer.value++
     }, 1000)
   }
   ```
4. Add it to the return statement:
   ```typescript
   return {
     // ... existing returns
     lobbyTimer,
     startLobbyTimer
   }
   ```
5. Call `startLobbyTimer()` in your `createGame` action
6. Display it in `LobbyView.vue`:
   ```vue
   <p>Time in lobby: {{ gameStore.lobbyTimer }}s</p>
   ```

**Watch it update automatically!** This demonstrates Vue's reactivity.

### Task 2.2: Create a computed player list

Add a computed property that shows only connected players:

1. In `stores/game.ts`:
   ```typescript
   const connectedPlayers = computed(() =>
     players.value.filter(p => p.is_connected)
   )
   ```
2. Return it from the store
3. Use it in `LobbyView.vue`:
   ```vue
   <p>Connected: {{ gameStore.connectedPlayers.length }}/{{ gameStore.players.length }}</p>
   ```

**Learning**: Computed values automatically recalculate when dependencies change.

### Task 2.3: Understand ref vs reactive

Create two versions of the same state:

```typescript
// Version 1: ref
const stateWithRef = ref({
  count: 0,
  name: "Alice"
})
stateWithRef.value.count++  // Need .value

// Version 2: reactive
const stateWithReactive = reactive({
  count: 0,
  name: "Alice"
})
stateWithReactive.count++  // No .value
```

**Question**: Which do you prefer? Most developers stick with `ref` for consistency.

---

## Exercise 3: Pinia Store Actions

**Goal**: Learn to manage state with async actions.

### Task 3.1: Add polling to refresh game state

Currently, you have `refreshGameState()`. Let's make it poll automatically:

1. In `stores/game.ts`, add a polling interval ref:
   ```typescript
   const pollingInterval = ref<number | null>(null)
   ```

2. Create start/stop polling actions:
   ```typescript
   function startPolling() {
     if (pollingInterval.value) return  // Already polling

     pollingInterval.value = window.setInterval(() => {
       refreshGameState()
     }, 2000)  // Poll every 2 seconds
   }

   function stopPolling() {
     if (pollingInterval.value) {
       clearInterval(pollingInterval.value)
       pollingInterval.value = null
     }
   }
   ```

3. Start polling when joining/creating a game:
   ```typescript
   async function createGame(nickname: string) {
     // ... existing code
     startPolling()  // Add this at the end
   }
   ```

4. Stop polling when leaving:
   ```typescript
   function leaveGame() {
     stopPolling()  // Add this first
     // ... existing reset code
   }
   ```

**Learning**: Actions can manage complex state changes and side effects.

### Task 3.2: Add optimistic UI updates

When a player changes their nickname, update the UI immediately:

1. Add a `updateNickname` action:
   ```typescript
   async function updateNickname(newNickname: string) {
     if (!playerId.value) return

     // Find current player
     const player = players.value.find(p => p.id === playerId.value)
     if (!player) return

     // Store old nickname
     const oldNickname = player.nickname

     // Optimistically update UI
     player.nickname = newNickname

     try {
       // Call API (you'd need to create this endpoint)
       await api.updatePlayerNickname(gameId.value!, playerId.value, newNickname)
     } catch (error) {
       // Revert on error
       player.nickname = oldNickname
       throw error
     }
   }
   ```

**Learning**: Optimistic updates make the UI feel faster.

---

## Exercise 4: Component Communication

**Goal**: Learn how components share data.

### Task 4.1: Create a PlayerCard component

1. Create `frontend/src/components/PlayerCard.vue`:
   ```vue
   <script setup lang="ts">
   import type { PlayerInfo } from '@/types/game'

   // Props - data passed from parent
   const props = defineProps<{
     player: PlayerInfo
     isCurrentPlayer?: boolean
   }>()

   // Emits - events sent to parent
   const emit = defineEmits<{
     kick: [playerId: string]
   }>()

   function handleKick() {
     emit('kick', props.player.id)
   }
   </script>

   <template>
     <div class="player-card">
       <h3>{{ player.nickname }}</h3>
       <p>Score: {{ player.score }}</p>
       <span v-if="player.is_host">👑 Host</span>
       <span v-if="!player.is_connected">🔴 Offline</span>
       <button v-if="!isCurrentPlayer" @click="handleKick">
         Kick
       </button>
     </div>
   </template>

   <style scoped>
   .player-card {
     border: 1px solid #ccc;
     padding: 1rem;
     margin: 0.5rem;
     border-radius: 8px;
   }
   </style>
   ```

2. Use it in `LobbyView.vue`:
   ```vue
   <script setup lang="ts">
   import PlayerCard from '@/components/PlayerCard.vue'
   import { useGameStore } from '@/stores/game'

   const gameStore = useGameStore()

   function handleKickPlayer(playerId: string) {
     console.log('Kick player:', playerId)
     // You'd implement the actual kick logic here
   }
   </script>

   <template>
     <div>
       <h1>Lobby</h1>
       <div>
         <PlayerCard
           v-for="player in gameStore.players"
           :key="player.id"
           :player="player"
           :is-current-player="player.id === gameStore.playerId"
           @kick="handleKickPlayer"
         />
       </div>
     </div>
   </template>
   ```

**Learning**:
- Props pass data **down** (parent → child)
- Events pass actions **up** (child → parent)

### Task 4.2: Use composables for shared logic

Create a reusable composition function:

1. Create `frontend/src/composables/useGameTimer.ts`:
   ```typescript
   import { ref, computed, onUnmounted } from 'vue'

   export function useGameTimer(durationSeconds: number) {
     const timeRemaining = ref(durationSeconds)
     const isRunning = ref(false)
     const intervalId = ref<number | null>(null)

     const progress = computed(() => {
       return (timeRemaining.value / durationSeconds) * 100
     })

     function start() {
       if (isRunning.value) return

       isRunning.value = true
       intervalId.value = window.setInterval(() => {
         if (timeRemaining.value > 0) {
           timeRemaining.value--
         } else {
           stop()
         }
       }, 1000)
     }

     function stop() {
       isRunning.value = false
       if (intervalId.value) {
         clearInterval(intervalId.value)
         intervalId.value = null
       }
     }

     function reset() {
       stop()
       timeRemaining.value = durationSeconds
     }

     // Cleanup on component unmount
     onUnmounted(() => {
       stop()
     })

     return {
       timeRemaining,
       progress,
       isRunning,
       start,
       stop,
       reset
     }
   }
   ```

2. Use it in a component:
   ```vue
   <script setup lang="ts">
   import { useGameTimer } from '@/composables/useGameTimer'

   const timer = useGameTimer(60)  // 60 second timer

   function startRound() {
     timer.start()
   }
   </script>

   <template>
     <div>
       <p>Time: {{ timer.timeRemaining }}s</p>
       <div class="progress-bar">
         <div :style="{ width: timer.progress + '%' }"></div>
       </div>
       <button @click="startRound">Start</button>
     </div>
   </template>
   ```

**Learning**: Composables let you reuse logic across components.

---

## Exercise 5: Vue Router

**Goal**: Add navigation and route guards.

### Task 5.1: Add a game route with parameters

1. In `frontend/src/router/index.ts`, add a route:
   ```typescript
   {
     path: '/game/:gameId',
     name: 'game',
     component: () => import('../views/GameView.vue'),
     props: true  // Pass route params as props
   }
   ```

2. Create `frontend/src/views/GameView.vue`:
   ```vue
   <script setup lang="ts">
   import { useRoute } from 'vue-router'
   import { useGameStore } from '@/stores/game'
   import { onMounted } from 'vue'

   const props = defineProps<{
     gameId: string
   }>()

   const route = useRoute()
   const gameStore = useGameStore()

   onMounted(async () => {
     // Load game data when component mounts
     if (props.gameId !== gameStore.gameId) {
       // Handle case where gameId in URL doesn't match store
       console.log('Game ID mismatch')
     }
   })
   </script>

   <template>
     <div>
       <h1>Game {{ gameId }}</h1>
       <p>Route param: {{ route.params.gameId }}</p>
     </div>
   </template>
   ```

### Task 5.2: Add navigation guards

Prevent users from accessing game routes if they're not in a game:

1. In `router/index.ts`:
   ```typescript
   import { useGameStore } from '@/stores/game'

   router.beforeEach((to, from, next) => {
     const gameStore = useGameStore()

     // Require being in a game to access game/lobby routes
     if ((to.name === 'game' || to.name === 'lobby') && !gameStore.isInGame) {
       next({ name: 'home' })  // Redirect to home
     } else {
       next()  // Allow navigation
     }
   })
   ```

**Learning**: Route guards protect routes and handle navigation logic.

---

## Exercise 6: Advanced TypeScript

**Goal**: Level up your TypeScript skills.

### Task 6.1: Use type guards

Create a function that safely checks types:

```typescript
// In types/game.ts
export function isPlayerInfo(obj: unknown): obj is PlayerInfo {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'nickname' in obj &&
    'score' in obj &&
    typeof (obj as PlayerInfo).id === 'string' &&
    typeof (obj as PlayerInfo).nickname === 'string' &&
    typeof (obj as PlayerInfo).score === 'number'
  )
}

// Usage
function processPlayer(data: unknown) {
  if (isPlayerInfo(data)) {
    // TypeScript knows data is PlayerInfo here
    console.log(data.nickname.toUpperCase())  // ✅ Safe
  }
}
```

### Task 6.2: Create discriminated unions

For handling different message types:

```typescript
type GameMessage =
  | { type: 'player_joined'; player: PlayerInfo }
  | { type: 'game_started'; round: number }
  | { type: 'error'; message: string }

function handleMessage(msg: GameMessage) {
  switch (msg.type) {
    case 'player_joined':
      // TypeScript knows msg.player exists here
      console.log('Player joined:', msg.player.nickname)
      break
    case 'game_started':
      // TypeScript knows msg.round exists here
      console.log('Game started, round:', msg.round)
      break
    case 'error':
      // TypeScript knows msg.message exists here
      console.error('Error:', msg.message)
      break
  }
}
```

**Learning**: Advanced TypeScript patterns make complex code safer.

---

## Challenge: Combine Everything

Create a complete feature using all concepts:

### Build a "Ready Check" System

1. **Types** (`types/game.ts`):
   ```typescript
   interface PlayerReadyState {
     playerId: string
     isReady: boolean
     timestamp: number
   }
   ```

2. **Store** (`stores/game.ts`):
   ```typescript
   const readyStates = ref<Map<string, PlayerReadyState>>(new Map())

   const allPlayersReady = computed(() => {
     if (players.value.length === 0) return false
     return players.value.every(p =>
       readyStates.value.get(p.id)?.isReady ?? false
     )
   })

   function toggleReady() {
     if (!playerId.value) return

     const currentState = readyStates.value.get(playerId.value)
     readyStates.value.set(playerId.value, {
       playerId: playerId.value,
       isReady: !currentState?.isReady,
       timestamp: Date.now()
     })

     // Would call API here
   }
   ```

3. **Component** (`components/ReadyCheck.vue`):
   ```vue
   <script setup lang="ts">
   import { useGameStore } from '@/stores/game'

   const gameStore = useGameStore()
   </script>

   <template>
     <div class="ready-check">
       <h3>Ready Check</h3>
       <button @click="gameStore.toggleReady">
         {{ gameStore.readyStates.get(gameStore.playerId!)?.isReady ? 'Not Ready' : 'Ready' }}
       </button>
       <p v-if="gameStore.allPlayersReady">All players ready! 🎉</p>
     </div>
   </template>
   ```

4. **Integration** (Use in `LobbyView.vue`)

---

## Debugging Tips

### Vue DevTools

Install the Vue DevTools browser extension to:
- Inspect component hierarchy
- View reactive state in real-time
- Track state changes
- Profile performance

### TypeScript Errors

When you see a TypeScript error:
1. Read it carefully - it tells you what's wrong
2. Hover over the red squiggly in VSCode/PyCharm
3. Check the type definition (Cmd+Click on type name)

### Common Patterns

```typescript
// Optional chaining (safe property access)
const nickname = player?.nickname ?? 'Unknown'

// Type assertion (when you know better than TypeScript)
const element = document.getElementById('app') as HTMLDivElement

// Array methods with types
const hostPlayer = players.value.find(p => p.is_host)
const playerNames = players.value.map(p => p.nickname)
const connectedCount = players.value.filter(p => p.is_connected).length
```

---

## Next Steps

After completing these exercises:
1. Try building a new feature from scratch
2. Refactor existing code to be more type-safe
3. Experiment with more advanced Vue patterns
4. Read the official Vue 3 and TypeScript docs

Questions? Want to add WebSockets now? Let me know!
