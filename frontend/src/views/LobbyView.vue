<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useClipboard } from '@/composables/useClipboard'

const router = useRouter()
const gameStore = useGameStore()
const { copied, copyToClipboard } = useClipboard()

onMounted(() => {
  if (!gameStore.isInGame) {
    router.push('/')
    return
  }
})

watch(
  () => gameStore.phase,
  (newPhase) => {
    if (newPhase && newPhase !== 'lobby') {
      router.push('/game')
    }
  },
)

function copyInviteCode() {
  if (gameStore.inviteCode) {
    copyToClipboard(gameStore.inviteCode)
  }
}

async function handleStartGame() {
  try {
    await gameStore.startGame()
    router.push('/game')
  } catch (e) {
    console.error('Failed to start game:', e)
  }
}

function leaveGame() {
  gameStore.leaveGame()
  router.push('/')
}

const canStartGame = () => {
  // Default min_players matches backend GameConfig default (2)
  const minPlayers = gameStore.config?.min_players ?? 2
  return gameStore.playerCount >= minPlayers
}
</script>

<template>
  <main class="lobby">
    <h1>Game Lobby</h1>

    <div class="invite-section">
      <h2>Invite Code</h2>
      <div class="invite-code">
        <span class="code">{{ gameStore.inviteCode }}</span>
        <button @click="copyInviteCode" class="copy-btn" :class="{ copied }">
          {{ copied ? 'Copied!' : 'Copy' }}
        </button>
      </div>
      <p class="invite-hint">Share this code with friends to join the game</p>
    </div>

    <div v-if="gameStore.error" class="error-message">
      {{ gameStore.error }}
    </div>

    <div class="players-section">
      <h2>Players ({{ gameStore.playerCount }}/{{ gameStore.config?.max_players ?? 8 }})</h2>
      <p class="min-players-hint" v-if="!canStartGame()">
        Need at least {{ gameStore.config?.min_players ?? 2 }} players to start
      </p>
      <ul class="players-list">
        <li v-for="player in gameStore.players" :key="player.id" class="player-item">
          <span class="player-name">{{ player.nickname }}</span>
          <span v-if="player.is_host" class="host-badge">Host</span>
          <span v-if="player.id === gameStore.playerId" class="you-badge">You</span>
        </li>
      </ul>
    </div>

    <div class="actions">
      <button
        v-if="gameStore.isHost"
        @click="handleStartGame"
        :disabled="!canStartGame() || gameStore.isLoading"
        class="start-btn"
      >
        {{ gameStore.isLoading ? 'Starting...' : 'Start Game' }}
      </button>
      <p v-else class="waiting-text">Waiting for host to start the game...</p>
      <button @click="leaveGame" class="leave-btn">Leave Game</button>
    </div>
  </main>
</template>

<style scoped>
.lobby {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
  animation: fadeInUp 0.4s var(--animation-smooth);
}

@media (min-width: 640px) {
  .lobby {
    padding: 2rem;
    max-width: 680px;
  }
}

@media (min-width: 1024px) {
  .lobby {
    max-width: 760px;
  }
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  text-transform: uppercase;
  font-size: clamp(1.5rem, 4vw, 2rem);
  letter-spacing: 0.05em;
}

.invite-section {
  background: var(--color-background-soft);
  padding: 1.25rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  text-align: center;
  border: 1px solid var(--color-border);
}

@media (min-width: 640px) {
  .invite-section {
    padding: 1.5rem;
  }
}

.invite-section h2 {
  margin-bottom: 1rem;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.invite-code {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

@media (min-width: 480px) {
  .invite-code {
    gap: 1rem;
  }
}

.code {
  font-size: clamp(1.5rem, 5vw, 2.25rem);
  font-weight: bold;
  letter-spacing: 0.3rem;
  font-family: var(--font-mono);
  padding: 0.5rem 1rem;
  background: var(--color-background);
  border-radius: 4px;
  border: 2px dashed var(--color-border);
}

.copy-btn {
  padding: 0.5rem 1rem;
  background: var(--color-text);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.copy-btn:hover {
  opacity: 0.9;
}

.copy-btn.copied {
  background: var(--color-success);
  color: var(--paper-light);
}

.invite-hint {
  font-family: var(--font-mono);
  margin-top: 1rem;
  font-size: 0.85rem;
  opacity: 0.7;
}

.players-section {
  margin-bottom: 2rem;
}

.players-section h2 {
  margin-bottom: 1rem;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.players-list {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}

@media (min-width: 640px) {
  .players-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
}

.player-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--color-background-soft);
  border-radius: 4px;
  border: 1px solid var(--color-border);
}

.player-name {
  flex: 1;
  font-family: var(--font-mono);
  font-weight: 600;
}

.host-badge,
.you-badge {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.host-badge {
  background: var(--accent-tertiary);
  color: var(--ink-dark);
}

.you-badge {
  background: var(--accent-primary);
  color: var(--paper-light);
}

.actions {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
}

@media (min-width: 480px) {
  .actions {
    flex-direction: row;
    justify-content: center;
    gap: 1rem;
  }
}

.leave-btn {
  padding: 0.75rem 2rem;
  background: var(--color-danger);
  color: var(--paper-light);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  width: 100%;
  max-width: 200px;
}

.leave-btn:hover {
  background: var(--color-danger-hover);
}

.error-message {
  font-family: var(--font-mono);
  background: var(--color-danger-light);
  color: var(--color-danger);
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  border: 1px solid var(--color-danger);
}

.min-players-hint {
  font-family: var(--font-mono);
  color: var(--color-warning);
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.start-btn {
  padding: 1rem 2rem;
  background: var(--accent-primary);
  color: var(--paper-light);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  width: 100%;
  max-width: 200px;
}

.start-btn:hover:not(:disabled) {
  background: var(--accent-primary-hover);
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.waiting-text {
  font-family: var(--font-mono);
  margin-bottom: 1rem;
  opacity: 0.7;
  font-style: italic;
}
</style>
