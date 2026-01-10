<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'

const router = useRouter()
const gameStore = useGameStore()

const pollingInterval = ref<number | null>(null)

onMounted(() => {
  if (!gameStore.isInGame) {
    router.push('/')
    return
  }

  pollingInterval.value = window.setInterval(() => {
    gameStore.refreshGameState()
  }, 2000)
})

onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
  }
})

function copyInviteCode() {
  if (gameStore.inviteCode) {
    navigator.clipboard.writeText(gameStore.inviteCode)
  }
}

function leaveGame() {
  gameStore.leaveGame()
  router.push('/')
}
</script>

<template>
  <main class="lobby">
    <h1>Game Lobby</h1>

    <div class="invite-section">
      <h2>Invite Code</h2>
      <div class="invite-code">
        <span class="code">{{ gameStore.inviteCode }}</span>
        <button @click="copyInviteCode" class="copy-btn">Copy</button>
      </div>
      <p class="invite-hint">Share this code with friends to join the game</p>
    </div>

    <div class="players-section">
      <h2>Players ({{ gameStore.playerCount }})</h2>
      <ul class="players-list">
        <li v-for="player in gameStore.players" :key="player.id" class="player-item">
          <span class="player-name">{{ player.nickname }}</span>
          <span v-if="player.is_host" class="host-badge">Host</span>
          <span v-if="player.id === gameStore.playerId" class="you-badge">You</span>
        </li>
      </ul>
    </div>

    <div class="actions">
      <button @click="leaveGame" class="leave-btn">Leave Game</button>
    </div>
  </main>
</template>

<style scoped>
.lobby {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
}

.invite-section {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  text-align: center;
}

.invite-section h2 {
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.invite-code {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
}

.code {
  font-size: 2rem;
  font-weight: bold;
  letter-spacing: 0.3rem;
  font-family: monospace;
  padding: 0.5rem 1rem;
  background: var(--color-background);
  border-radius: 4px;
}

.copy-btn {
  padding: 0.5rem 1rem;
  background: var(--color-text);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.copy-btn:hover {
  opacity: 0.9;
}

.invite-hint {
  margin-top: 1rem;
  font-size: 0.9rem;
  opacity: 0.7;
}

.players-section {
  margin-bottom: 2rem;
}

.players-section h2 {
  margin-bottom: 1rem;
}

.players-list {
  list-style: none;
  padding: 0;
}

.player-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--color-background-soft);
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.player-name {
  flex: 1;
}

.host-badge,
.you-badge {
  font-size: 0.8rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.host-badge {
  background: #ffd700;
  color: #000;
}

.you-badge {
  background: #4caf50;
  color: #fff;
}

.actions {
  text-align: center;
}

.leave-btn {
  padding: 0.75rem 2rem;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.leave-btn:hover {
  background: #c82333;
}
</style>
