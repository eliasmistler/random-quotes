<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useClipboard } from '@/composables/useClipboard'
import ChatWindow from '@/components/ChatWindow.vue'

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
  const minPlayers = gameStore.config?.min_players ?? 2
  return gameStore.playerCount >= minPlayers
}

const canAddBot = () => {
  const maxPlayers = gameStore.config?.max_players ?? 8
  return gameStore.playerCount < maxPlayers
}

async function handleAddBot() {
  try {
    await gameStore.addBot()
  } catch (e) {
    console.error('Failed to add bot:', e)
  }
}
</script>

<template>
  <main class="lobby">
    <div class="title-row">
      <h1 class="page-title">Game Lobby</h1>
      <span class="wow-bubble">snip happens</span>
    </div>

    <!-- Invite Code Section - Paper scrap style -->
    <div class="invite-section">
      <div class="tape-strip"></div>
      <h2>Share This Code</h2>
      <div class="invite-code-display">
        <span
          v-for="(char, index) in (gameStore.inviteCode || '').split('')"
          :key="index"
          class="code-letter"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >{{ char }}</span>
      </div>
      <button @click="copyInviteCode" class="copy-btn" :class="{ copied }">
        {{ copied ? 'Copied!' : 'Copy Code' }}
      </button>
      <p class="invite-hint">Share this code with friends to join</p>
    </div>

    <div v-if="gameStore.error" class="error-message">
      {{ gameStore.error }}
    </div>

    <!-- Players Section -->
    <div class="players-section">
      <h2>
        Players
        <span class="player-count">({{ gameStore.playerCount }}/{{ gameStore.config?.max_players ?? 8 }})</span>
      </h2>
      <p class="min-players-hint" v-if="!canStartGame()">
        Need {{ gameStore.config?.min_players ?? 2 }} players minimum
      </p>
      <ul class="players-list">
        <li
          v-for="(player, index) in gameStore.players"
          :key="player.id"
          class="player-item"
          :class="{ 'is-bot': player.is_bot }"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <span class="player-name">{{ player.nickname }}</span>
          <div class="badges">
            <span v-if="player.is_bot" class="badge bot-badge">Bot</span>
            <span v-if="player.is_host" class="badge host-badge">Host</span>
            <span v-if="player.id === gameStore.playerId" class="badge you-badge">You</span>
          </div>
        </li>
      </ul>
      <button
        v-if="gameStore.isHost && canAddBot()"
        @click="handleAddBot"
        :disabled="gameStore.isLoading"
        class="add-bot-btn"
      >
        + Add Bot
      </button>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button
        v-if="gameStore.isHost"
        @click="handleStartGame"
        :disabled="!canStartGame() || gameStore.isLoading"
        class="start-btn"
      >
        {{ gameStore.isLoading ? 'Starting...' : 'Start Game' }}
      </button>
      <p v-else class="waiting-text">Waiting for host to start...</p>
      <button @click="leaveGame" class="leave-btn">Leave Game</button>
    </div>

    <!-- Chat Window -->
    <ChatWindow />
  </main>
</template>

<style scoped>
.lobby {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1rem;
  padding-bottom: 120px; /* Space for chat window */
  animation: fadeInUp 0.4s var(--animation-smooth);
}

@media (min-width: 640px) {
  .lobby {
    padding: 2.5rem 2rem;
  }
}

/* ==========================================================================
   PAGE TITLE
   ========================================================================== */

.title-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.page-title {
  text-align: center;
  margin-bottom: 0;
  font-family: var(--font-headline-2);
  font-size: clamp(1.75rem, 5vw, 2.5rem);
  letter-spacing: 0.08em;
  color: var(--color-heading);
}

.wow-bubble {
  display: inline-block;
  background: var(--accent-yellow);
  color: var(--ink-black);
  font-family: var(--font-display-1);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.4rem 0.8rem;
  border-radius: 50% 50% 50% 10%;
  transform: rotate(8deg);
  box-shadow: var(--shadow-paper);
  text-transform: lowercase;
  letter-spacing: 0.02em;
  position: relative;
  animation: wobble 2s ease-in-out infinite;
}

.wow-bubble::before {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 8px;
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 4px solid transparent;
  border-top: 8px solid var(--accent-yellow);
  transform: rotate(-15deg);
}

@keyframes wobble {
  0%, 100% { transform: rotate(8deg) scale(1); }
  25% { transform: rotate(10deg) scale(1.02); }
  75% { transform: rotate(6deg) scale(0.98); }
}

/* ==========================================================================
   INVITE SECTION
   ========================================================================== */

.invite-section {
  background: var(--scrap-white);
  padding: 2rem 1.5rem;
  text-align: center;
  margin-bottom: 2rem;
  position: relative;
  box-shadow: var(--shadow-paper);
  transform: rotate(-0.5deg);
}

@media (min-width: 640px) {
  .invite-section {
    padding: 2.5rem 2rem;
  }
}

.tape-strip {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%) rotate(2deg);
  width: 70px;
  height: 22px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 200, 0.85) 0%,
    rgba(255, 255, 180, 0.7) 100%
  );
  box-shadow:
    inset 0 0 4px rgba(255, 255, 255, 0.5),
    0 2px 4px rgba(0, 0, 0, 0.1);
}

.invite-section h2 {
  font-family: var(--font-typewriter);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 1rem;
  color: var(--color-text-muted);
}

.invite-code-display {
  display: flex;
  justify-content: center;
  gap: 0.25rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

@media (min-width: 640px) {
  .invite-code-display {
    gap: 0.4rem;
  }
}

.code-letter {
  display: inline-block;
  font-size: clamp(1.75rem, 6vw, 2.5rem);
  font-weight: 700;
  padding: 0.3em 0.25em;
  background: var(--scrap-yellow);
  color: var(--ink-black);
  box-shadow: var(--shadow-paper);
  animation: paperDrop 0.4s var(--animation-smooth) backwards;
  font-family: var(--font-headline-2);
  letter-spacing: 0.05em;
}

.code-letter:nth-child(odd) {
  transform: rotate(-2deg);
  font-family: var(--font-headline-1);
  background: var(--scrap-cream);
}

.code-letter:nth-child(even) {
  transform: rotate(1.5deg);
  font-family: var(--font-headline-4);
  background: var(--scrap-pink);
}

.code-letter:nth-child(3n) {
  background: var(--scrap-blue);
  font-family: var(--font-display-1);
}

.copy-btn {
  padding: 0.75rem 1.5rem;
  background: var(--ink-black);
  color: var(--scrap-white);
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  box-shadow: var(--shadow-paper);
  margin-bottom: 0.75rem;
}

.copy-btn:hover {
  background: var(--ink-charcoal);
  transform: rotate(1deg) scale(1.02);
}

.copy-btn.copied {
  background: var(--color-success);
}

.invite-hint {
  font-family: var(--font-typewriter);
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

/* ==========================================================================
   ERROR MESSAGE
   ========================================================================== */

.error-message {
  font-family: var(--font-typewriter);
  background: var(--color-danger-light);
  color: var(--color-danger);
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  border-left: 4px solid var(--color-danger);
  animation: shake 0.4s ease;
}

/* ==========================================================================
   PLAYERS SECTION
   ========================================================================== */

.players-section {
  margin-bottom: 2rem;
}

.players-section h2 {
  font-family: var(--font-headline-2);
  font-size: 1.1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.player-count {
  font-family: var(--font-typewriter);
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-weight: 400;
}

.min-players-hint {
  font-family: var(--font-typewriter);
  color: var(--color-warning);
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--scrap-yellow);
  display: inline-block;
  transform: rotate(-0.5deg);
}

.players-list {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}

@media (min-width: 480px) {
  .players-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
}

.player-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--scrap-newsprint);
  box-shadow: var(--shadow-paper);
  animation: paperDrop 0.4s var(--animation-smooth) backwards;
}

.player-item:nth-child(odd) {
  transform: rotate(-0.5deg);
}

.player-item:nth-child(even) {
  transform: rotate(0.5deg);
}

.player-name {
  font-family: var(--font-typewriter);
  font-weight: 700;
  font-size: 1rem;
  color: var(--ink-black);
}

.badges {
  display: flex;
  gap: 0.35rem;
}

.badge {
  font-family: var(--font-typewriter);
  font-size: 0.65rem;
  padding: 0.2rem 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
}

.host-badge {
  background: var(--accent-yellow);
  color: var(--ink-black);
}

.you-badge {
  background: var(--accent-red);
  color: white;
}

.bot-badge {
  background: var(--scrap-blue);
  color: var(--ink-black);
}

.player-item.is-bot {
  background: var(--scrap-blue);
  opacity: 0.9;
}

.add-bot-btn {
  margin-top: 1rem;
  padding: 0.6rem 1.2rem;
  background: var(--scrap-newsprint);
  color: var(--ink-black);
  border: 2px dashed var(--ink-grey);
  cursor: pointer;
  font-family: var(--font-typewriter);
  font-size: 0.85rem;
  box-shadow: var(--shadow-paper);
}

.add-bot-btn:hover:not(:disabled) {
  background: var(--scrap-blue);
  border-color: var(--ink-black);
  transform: rotate(0.5deg);
}

.add-bot-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ==========================================================================
   ACTIONS
   ========================================================================== */

.actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

@media (min-width: 480px) {
  .actions {
    flex-direction: row;
    justify-content: center;
    gap: 1rem;
  }
}

.start-btn {
  padding: 1rem 2.5rem;
  background: var(--accent-red);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  box-shadow: var(--shadow-paper);
  transform: rotate(-0.5deg);
  width: 100%;
  max-width: 220px;
}

.start-btn:hover:not(:disabled) {
  background: var(--accent-red-dark);
  box-shadow: var(--shadow-paper-hover);
  transform: rotate(0.5deg) scale(1.02);
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.waiting-text {
  font-family: var(--font-typewriter);
  color: var(--color-text-muted);
  font-style: italic;
  padding: 1rem;
}

.leave-btn {
  padding: 0.75rem 1.5rem;
  background: var(--scrap-newsprint);
  color: var(--color-danger);
  border: 2px solid var(--color-danger);
  cursor: pointer;
  font-size: 0.9rem;
  box-shadow: var(--shadow-paper);
  width: 100%;
  max-width: 180px;
}

.leave-btn:hover {
  background: var(--color-danger);
  color: white;
  transform: rotate(1deg);
}

/* ==========================================================================
   ANIMATIONS
   ========================================================================== */

@keyframes paperDrop {
  0% {
    opacity: 0;
    transform: translateY(-30px) rotate(-10deg);
  }
  60% {
    transform: translateY(5px) rotate(2deg);
  }
  100% {
    opacity: 1;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-3px); }
  20%, 40%, 60%, 80% { transform: translateX(3px); }
}
</style>
