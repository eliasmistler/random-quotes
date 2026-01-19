<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { loadSession, clearSession, type GameSession } from '@/utils/session'
import * as api from '@/api/game'

const router = useRouter()
const gameStore = useGameStore()

const nickname = ref('')
const inviteCode = ref('')
const isCreating = ref(false)
const isJoining = ref(false)

// Rejoin dialog state
const showRejoinDialog = ref(false)
const pendingSession = ref<GameSession | null>(null)
const isRejoining = ref(false)

async function handleCreateGame() {
  if (!nickname.value.trim()) return

  isCreating.value = true
  try {
    await gameStore.createGame(nickname.value.trim())
    router.push('/lobby')
  } catch (e) {
    console.error('Failed to create game:', e)
  } finally {
    isCreating.value = false
  }
}

async function handleJoinGame() {
  if (!nickname.value.trim() || !inviteCode.value.trim()) return

  isJoining.value = true
  try {
    await gameStore.joinGame(inviteCode.value.trim(), nickname.value.trim())
    router.push('/lobby')
  } catch (e) {
    console.error('Failed to join game:', e)
  } finally {
    isJoining.value = false
  }
}

async function checkExistingSession() {
  // Don't check if already in a game
  if (gameStore.isInGame) return

  const session = loadSession()
  if (!session) return

  try {
    // Validate session with backend
    const state = await api.getGameState(session.gameId, session.playerId)

    // If game is over, don't offer to rejoin
    if (state.phase === 'game_over') {
      clearSession()
      return
    }

    // Session is valid - show rejoin dialog
    pendingSession.value = session
    showRejoinDialog.value = true
  } catch {
    // Game or player not found - clear stale session
    clearSession()
  }
}

async function handleRejoin() {
  if (!pendingSession.value) return

  isRejoining.value = true
  try {
    const phase = await gameStore.reconnectToGame(
      pendingSession.value.gameId,
      pendingSession.value.playerId
    )

    showRejoinDialog.value = false

    // Navigate based on phase
    if (phase === 'lobby') {
      router.push('/lobby')
    } else {
      router.push('/game')
    }
  } catch (e) {
    console.error('Failed to rejoin game:', e)
    // Clear invalid session
    clearSession()
    showRejoinDialog.value = false
    pendingSession.value = null
  } finally {
    isRejoining.value = false
  }
}

function handleStartFresh() {
  clearSession()
  showRejoinDialog.value = false
  pendingSession.value = null
}

onMounted(() => {
  checkExistingSession()
})

// Letter styles for the magazine cutout title effect - split into two words
interface RansomLetter {
  char: string
  font: string
  bg: string
  rotate: number
  color?: string
}

const randomLetters: RansomLetter[] = [
  { char: 'R', font: 'headline-1', bg: 'cream', rotate: -3 },
  { char: 'A', font: 'headline-2', bg: 'yellow', rotate: 2 },
  { char: 'N', font: 'display-1', bg: 'pink', rotate: -1 },
  { char: 'D', font: 'headline-3', bg: 'white', rotate: 1.5 },
  { char: 'O', font: 'headline-4', bg: 'blue', rotate: -2 },
  { char: 'M', font: 'body-2', bg: 'orange', rotate: 2.5 },
]

const quotesLetters: RansomLetter[] = [
  { char: 'Q', font: 'headline-6', bg: 'newsprint', rotate: -1.5 },
  { char: 'U', font: 'display-2', bg: 'cream', rotate: 3, color: 'red' },
  { char: 'O', font: 'headline-2', bg: 'yellow', rotate: -2 },
  { char: 'T', font: 'headline-1', bg: 'green', rotate: 1 },
  { char: 'E', font: 'display-1', bg: 'pink', rotate: -2.5 },
  { char: 'S', font: 'headline-3', bg: 'blue', rotate: 2 },
]
</script>

<template>
  <main class="home">
    <!-- Random Quotes Title - Each letter is a cutout -->
    <h1 class="logo-title">
      <span class="word">
        <span
          v-for="(letter, index) in randomLetters"
          :key="'random-' + index"
          class="letter"
          :class="[
            letter.font ? `font-${letter.font}` : '',
            letter.bg ? `bg-${letter.bg}` : '',
            letter.color ? `color-${letter.color}` : ''
          ]"
          :style="{
            transform: `rotate(${letter.rotate}deg)`,
            animationDelay: `${index * 0.05}s`
          }"
        >{{ letter.char }}</span>
      </span>
      <span class="word">
        <span
          v-for="(letter, index) in quotesLetters"
          :key="'quotes-' + index"
          class="letter"
          :class="[
            letter.font ? `font-${letter.font}` : '',
            letter.bg ? `bg-${letter.bg}` : '',
            letter.color ? `color-${letter.color}` : ''
          ]"
          :style="{
            transform: `rotate(${letter.rotate}deg)`,
            animationDelay: `${(index + randomLetters.length) * 0.05}s`
          }"
        >{{ letter.char }}</span>
      </span>
    </h1>

    <p class="subtitle">
      <span class="subtitle-inner">The Word Heist of the Century</span>
    </p>

    <!-- Main form card with tape effect -->
    <div class="game-forms">
      <div class="tape-strip"></div>

      <div class="form-section">
        <label for="nickname">Your Alias</label>
        <input
          id="nickname"
          v-model="nickname"
          type="text"
          placeholder="Enter your nickname..."
          maxlength="20"
          autocomplete="off"
        />
      </div>

      <div v-if="gameStore.error" class="error-message">
        {{ gameStore.error }}
      </div>

      <div class="actions">
        <button
          @click="handleCreateGame"
          :disabled="!nickname.trim() || isCreating || isJoining"
          class="create-btn"
        >
          {{ isCreating ? 'Creating...' : 'Start New Game' }}
        </button>

        <div class="divider">
          <span class="divider-text">or join existing</span>
        </div>

        <div class="join-section">
          <input
            v-model="inviteCode"
            type="text"
            placeholder="CODE"
            maxlength="6"
            class="invite-input"
            autocomplete="off"
          />
          <button
            @click="handleJoinGame"
            :disabled="!nickname.trim() || !inviteCode.trim() || isCreating || isJoining"
            class="join-btn"
          >
            {{ isJoining ? '...' : 'Join' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rejoin Dialog -->
    <div v-if="showRejoinDialog" class="rejoin-overlay">
      <div class="rejoin-dialog">
        <div class="tape-strip"></div>
        <h2>Rejoin Game?</h2>
        <p class="rejoin-message">
          You were playing as <strong>{{ pendingSession?.nickname }}</strong>
        </p>
        <p class="game-code">Game: {{ pendingSession?.inviteCode }}</p>
        <div class="dialog-actions">
          <button
            @click="handleRejoin"
            class="rejoin-btn"
            :disabled="isRejoining"
          >
            {{ isRejoining ? 'Rejoining...' : 'Rejoin Game' }}
          </button>
          <button
            @click="handleStartFresh"
            class="fresh-btn"
            :disabled="isRejoining"
          >
            Start Fresh
          </button>
        </div>
      </div>
    </div>

    <!-- Decorative scattered letters -->
    <div class="scattered-letters" aria-hidden="true">
      <span class="scattered-letter l1">?</span>
      <span class="scattered-letter l2">!</span>
      <span class="scattered-letter l3">&</span>
      <span class="scattered-letter l4">$</span>
      <span class="scattered-letter l5">@</span>
    </div>
  </main>
</template>

<style scoped>
.home {
  max-width: 520px;
  margin: 0 auto;
  padding: 2rem 1rem;
  text-align: center;
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

@media (min-width: 640px) {
  .home {
    padding: 3rem 2rem;
  }
}

/* ==========================================================================
   RANDOM QUOTES TITLE - Each letter is a paper cutout
   ========================================================================== */

.logo-title {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.15rem;
  margin-bottom: 1rem;
  line-height: 1;
}

@media (min-width: 640px) {
  .logo-title {
    gap: 0.25rem;
    margin-bottom: 1.5rem;
  }
}

.letter {
  display: inline-block;
  padding: 0.2em 0.15em;
  font-size: clamp(2rem, 8vw, 3.5rem);
  line-height: 1;
  box-shadow: var(--shadow-paper);
  animation: paperDrop 0.5s var(--animation-smooth) backwards;
  transition: transform 0.15s ease;
}

.letter:hover {
  transform: scale(1.1) rotate(0deg) !important;
  box-shadow: var(--shadow-lifted);
  z-index: 10;
}

/* Word wrapper to prevent mid-word breaks */
.word {
  display: inline-flex;
  gap: 0.15rem;
  white-space: nowrap;
}

@media (min-width: 640px) {
  .word {
    gap: 0.25rem;
  }
}

/* Font classes */
.font-headline-1 { font-family: var(--font-headline-1); }
.font-headline-2 { font-family: var(--font-headline-2); }
.font-headline-3 { font-family: var(--font-headline-3); font-style: italic; }
.font-headline-4 { font-family: var(--font-headline-4); }
.font-headline-6 { font-family: var(--font-headline-6); }
.font-display-1 { font-family: var(--font-display-1); }
.font-display-2 { font-family: var(--font-display-2); }
.font-body-2 { font-family: var(--font-body-2); }

/* Background colors */
.bg-white { background-color: var(--scrap-white); color: var(--ink-black); }
.bg-cream { background-color: var(--scrap-cream); color: var(--ink-black); }
.bg-yellow { background-color: var(--scrap-yellow); color: var(--ink-black); }
.bg-pink { background-color: var(--scrap-pink); color: var(--ink-black); }
.bg-blue { background-color: var(--scrap-blue); color: var(--ink-black); }
.bg-green { background-color: var(--scrap-green); color: var(--ink-black); }
.bg-orange { background-color: var(--scrap-orange); color: var(--ink-black); }
.bg-newsprint { background-color: var(--scrap-newsprint); color: var(--ink-black); }

/* Text color override */
.color-red { color: var(--accent-red) !important; }

/* ==========================================================================
   SUBTITLE
   ========================================================================== */

.subtitle {
  margin-bottom: 2rem;
  animation: fadeInUp 0.6s var(--animation-smooth) 0.5s backwards;
}

@media (min-width: 640px) {
  .subtitle {
    margin-bottom: 3rem;
  }
}

.subtitle-inner {
  font-family: var(--font-typewriter);
  font-size: clamp(0.85rem, 2.5vw, 1rem);
  color: var(--color-text-muted);
  background: var(--scrap-newsprint);
  padding: 0.5rem 1rem;
  display: inline-block;
  transform: rotate(-1deg);
  box-shadow: var(--shadow-paper);
}

/* ==========================================================================
   FORM CARD
   ========================================================================== */

.game-forms {
  background: var(--scrap-white);
  padding: 2rem 1.5rem;
  position: relative;
  box-shadow: var(--shadow-paper);
  transform: rotate(0.5deg);
  animation: fadeInUp 0.6s var(--animation-smooth) 0.7s backwards;
}

@media (min-width: 640px) {
  .game-forms {
    padding: 2.5rem 2rem;
  }
}

/* Tape strip at top */
.tape-strip {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%) rotate(-2deg);
  width: 80px;
  height: 24px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 200, 0.85) 0%,
    rgba(255, 255, 180, 0.7) 100%
  );
  box-shadow:
    inset 0 0 4px rgba(255, 255, 255, 0.5),
    0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section label {
  display: block;
  margin-bottom: 0.5rem;
  text-align: left;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
}

.form-section input {
  width: 100%;
  padding: 1rem;
  font-size: 1.1rem;
  border: 2px solid var(--ink-charcoal);
  background: var(--scrap-newsprint);
}

.form-section input:focus {
  border-color: var(--accent-red);
  background: var(--scrap-white);
}

/* ==========================================================================
   ERROR MESSAGE
   ========================================================================== */

.error-message {
  font-family: var(--font-typewriter);
  background: var(--color-danger-light);
  color: var(--color-danger);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  border-left: 4px solid var(--color-danger);
  text-align: left;
  animation: shake 0.4s ease;
}

/* ==========================================================================
   ACTION BUTTONS
   ========================================================================== */

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.create-btn {
  width: 100%;
  padding: 1.1rem;
  font-size: 1.1rem;
  background: var(--accent-red);
  color: white;
  border: none;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
  transform: rotate(-0.5deg);
  letter-spacing: 0.06em;
}

.create-btn:hover:not(:disabled) {
  background: var(--accent-red-dark);
  box-shadow: var(--shadow-paper-hover);
  transform: rotate(0.5deg) scale(1.02);
}

.create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* ==========================================================================
   DIVIDER
   ========================================================================== */

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0.5rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 2px;
  background: repeating-linear-gradient(
    90deg,
    var(--ink-charcoal) 0px,
    var(--ink-charcoal) 4px,
    transparent 4px,
    transparent 8px
  );
}

.divider-text {
  font-family: var(--font-typewriter);
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  white-space: nowrap;
}

/* ==========================================================================
   JOIN SECTION
   ========================================================================== */

.join-section {
  display: flex;
  gap: 0.5rem;
}

.invite-input {
  flex: 1;
  padding: 0.875rem;
  font-size: 1.2rem;
  text-transform: uppercase;
  text-align: center;
  letter-spacing: 0.3em;
  font-weight: 700;
  background: var(--scrap-yellow);
  border: 2px solid var(--ink-charcoal);
  min-width: 0;
}

.invite-input::placeholder {
  letter-spacing: 0.15em;
  font-weight: 400;
  opacity: 0.6;
}

.invite-input:focus {
  background: var(--scrap-white);
}

.join-btn {
  padding: 0.875rem 1.5rem;
  font-size: 1rem;
  background: var(--ink-black);
  color: var(--scrap-white);
  border: none;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
  white-space: nowrap;
}

.join-btn:hover:not(:disabled) {
  background: var(--ink-charcoal);
  transform: rotate(1deg) scale(1.02);
}

.join-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ==========================================================================
   SCATTERED DECORATIVE LETTERS
   ========================================================================== */

.scattered-letters {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: -1;
}

.scattered-letter {
  position: absolute;
  font-size: clamp(2rem, 5vw, 4rem);
  opacity: 0.08;
  font-weight: 700;
}

.l1 {
  font-family: var(--font-headline-1);
  top: 10%;
  left: 5%;
  transform: rotate(-15deg);
}

.l2 {
  font-family: var(--font-display-1);
  top: 20%;
  right: 8%;
  transform: rotate(20deg);
  color: var(--accent-red);
  opacity: 0.1;
}

.l3 {
  font-family: var(--font-headline-2);
  bottom: 25%;
  left: 10%;
  transform: rotate(10deg);
}

.l4 {
  font-family: var(--font-display-2);
  bottom: 15%;
  right: 5%;
  transform: rotate(-25deg);
}

.l5 {
  font-family: var(--font-headline-3);
  top: 60%;
  left: 3%;
  transform: rotate(5deg);
}

/* ==========================================================================
   ANIMATIONS
   ========================================================================== */

@keyframes paperDrop {
  0% {
    opacity: 0;
    transform: translateY(-40px) rotate(-15deg);
  }
  60% {
    transform: translateY(5px) rotate(3deg);
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

/* ==========================================================================
   REJOIN DIALOG
   ========================================================================== */

.rejoin-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
  animation: fadeIn 0.2s ease;
}

.rejoin-dialog {
  background: var(--scrap-white);
  padding: 2rem 1.5rem;
  max-width: 360px;
  width: 100%;
  position: relative;
  box-shadow: var(--shadow-lifted);
  transform: rotate(-1deg);
  animation: dialogSlideIn 0.3s var(--animation-smooth);
}

.rejoin-dialog h2 {
  font-family: var(--font-headline-1);
  font-size: 1.5rem;
  margin-bottom: 1rem;
  text-align: center;
}

.rejoin-message {
  font-family: var(--font-typewriter);
  text-align: center;
  margin-bottom: 0.5rem;
}

.rejoin-message strong {
  color: var(--accent-red);
}

.game-code {
  font-family: var(--font-typewriter);
  text-align: center;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
  letter-spacing: 0.1em;
}

.dialog-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dialog-actions .rejoin-btn {
  width: 100%;
  padding: 1rem;
  font-size: 1rem;
  background: var(--accent-red);
  color: white;
  border: none;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
  letter-spacing: 0.06em;
}

.dialog-actions .rejoin-btn:hover:not(:disabled) {
  background: var(--accent-red-dark);
  transform: scale(1.02);
}

.dialog-actions .rejoin-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dialog-actions .fresh-btn {
  width: 100%;
  padding: 0.875rem;
  font-size: 0.9rem;
  background: transparent;
  color: var(--ink-charcoal);
  border: 2px solid var(--ink-charcoal);
  cursor: pointer;
  letter-spacing: 0.04em;
}

.dialog-actions .fresh-btn:hover:not(:disabled) {
  background: var(--scrap-newsprint);
}

.dialog-actions .fresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes dialogSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) rotate(-1deg);
  }
  to {
    opacity: 1;
    transform: translateY(0) rotate(-1deg);
  }
}
</style>
