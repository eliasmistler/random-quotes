<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'

const router = useRouter()
const gameStore = useGameStore()

const timerInterval = ref<number | null>(null)
const selectedTiles = ref<string[]>([])
const remainingSeconds = ref<number | null>(null)

// Computed properties for timer display
const timerDisplay = computed(() => {
  if (remainingSeconds.value === null) return null
  const mins = Math.floor(remainingSeconds.value / 60)
  const secs = remainingSeconds.value % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

const timerUrgent = computed(() => remainingSeconds.value !== null && remainingSeconds.value <= 15)

// Submission progress
const submissionProgress = computed(() => {
  if (!gameStore.currentRound) return null
  return {
    submitted: gameStore.currentRound.submission_count,
    total: gameStore.currentRound.total_players,
  }
})

// Overrule vote progress for all players
const overruleVoteProgress = computed(() => {
  if (!gameStore.currentRound || !gameStore.judgePickedSelf) return null
  const votes = gameStore.currentRound.overrule_votes
  const totalVoters = gameStore.players.length - 1 // Exclude judge
  const votesForOverrule = Object.values(votes).filter((v) => v === true).length
  const votesAgainst = Object.values(votes).filter((v) => v === false).length
  return {
    votesFor: votesForOverrule,
    votesAgainst,
    totalVoted: Object.keys(votes).length,
    totalVoters,
  }
})

function updateTimer() {
  if (!gameStore.currentRound?.started_at || !gameStore.config) {
    remainingSeconds.value = null
    return
  }

  const startedAt = new Date(gameStore.currentRound.started_at).getTime()
  const timeLimit = gameStore.config.submission_time_seconds * 1000
  const elapsed = Date.now() - startedAt
  const remaining = Math.max(0, Math.ceil((timeLimit - elapsed) / 1000))
  remainingSeconds.value = remaining
}

// Watch for phase changes to start/stop timer
watch(
  () => gameStore.phase,
  (newPhase) => {
    if (newPhase === 'round_submission') {
      updateTimer()
      if (!timerInterval.value) {
        timerInterval.value = window.setInterval(updateTimer, 1000)
      }
    } else {
      remainingSeconds.value = null
      if (timerInterval.value) {
        clearInterval(timerInterval.value)
        timerInterval.value = null
      }
    }
  },
)

onMounted(() => {
  if (!gameStore.isInGame) {
    router.push('/')
    return
  }

  // Start timer if already in submission phase
  if (gameStore.phase === 'round_submission') {
    updateTimer()
    timerInterval.value = window.setInterval(updateTimer, 1000)
  }
})

onUnmounted(() => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
  }
})

function toggleTile(tile: string) {
  const index = selectedTiles.value.indexOf(tile)
  if (index === -1) {
    selectedTiles.value.push(tile)
  } else {
    selectedTiles.value.splice(index, 1)
  }
}

async function handleSubmit() {
  if (selectedTiles.value.length === 0) return

  try {
    await gameStore.submitResponse(selectedTiles.value)
    selectedTiles.value = []
  } catch (e) {
    console.error('Failed to submit:', e)
  }
}

async function handleSelectWinner(playerId: string) {
  try {
    await gameStore.selectWinner(playerId)
  } catch (e) {
    console.error('Failed to select winner:', e)
  }
}

async function handleAdvance() {
  try {
    await gameStore.advanceRound()
  } catch (e) {
    console.error('Failed to advance:', e)
  }
}

async function handleOverruleVote(voteToOverrule: boolean) {
  try {
    await gameStore.castOverruleVote(voteToOverrule)
  } catch (e) {
    console.error('Failed to cast overrule vote:', e)
  }
}

async function handleWinnerVote(playerId: string) {
  try {
    await gameStore.castWinnerVote(playerId)
  } catch (e) {
    console.error('Failed to cast winner vote:', e)
  }
}

function leaveGame() {
  gameStore.leaveGame()
  router.push('/')
}

function getPlayerNickname(playerId: string): string {
  return gameStore.players.find((p) => p.id === playerId)?.nickname ?? 'Unknown'
}
</script>

<template>
  <main class="game">
    <header class="game-header">
      <div class="round-info" v-if="gameStore.currentRound">
        Round {{ gameStore.currentRound.round_number }}
      </div>
      <div class="scores">
        <div
          v-for="player in gameStore.players"
          :key="player.id"
          class="player-score"
          :class="{ 'is-you': player.id === gameStore.playerId }"
        >
          {{ player.nickname }}: {{ player.score }}
        </div>
      </div>
    </header>

    <div v-if="gameStore.error" class="error-message">
      {{ gameStore.error }}
    </div>

    <!-- Submission Phase -->
    <div v-if="gameStore.phase === 'round_submission'" class="phase-content">
      <div class="prompt-card">
        <h2>{{ gameStore.currentRound?.prompt.text }}</h2>
        <p class="judge-info">Judge will be selected after all players submit</p>
      </div>

      <!-- Timer and Progress Bar -->
      <div class="submission-status">
        <div class="timer" :class="{ urgent: timerUrgent }">
          <span class="timer-icon">⏱</span>
          <span class="timer-value">{{ timerDisplay ?? '--:--' }}</span>
        </div>
        <div class="progress-indicator">
          <span class="progress-text">
            {{ submissionProgress?.submitted ?? 0 }}/{{ submissionProgress?.total ?? 0 }} submitted
          </span>
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{
                width: submissionProgress
                  ? `${(submissionProgress.submitted / submissionProgress.total) * 100}%`
                  : '0%',
              }"
            ></div>
          </div>
        </div>
      </div>

      <div v-if="gameStore.hasSubmitted" class="waiting-message">
        <p>Response submitted! Waiting for other players...</p>
        <p class="progress-detail">
          {{ submissionProgress?.submitted }}/{{ submissionProgress?.total }} players have submitted
        </p>
      </div>

      <div v-else class="submission-area">
        <div class="submission-layout">
          <div class="submission-controls">
            <p class="instruction">Select tiles to create your answer:</p>

            <div class="selected-preview">
              <span v-if="selectedTiles.length === 0" class="placeholder">
                Click tiles below to build your answer
              </span>
              <span v-else class="preview-text">{{ selectedTiles.join(' ') }}</span>
            </div>

            <button
              class="submit-btn"
              :disabled="selectedTiles.length === 0 || gameStore.isLoading"
              @click="handleSubmit"
            >
              {{ gameStore.isLoading ? 'Submitting...' : 'Submit Answer' }}
            </button>
          </div>

          <div class="tiles-section">
            <div class="tiles-grid">
              <button
                v-for="(tile, index) in gameStore.myTiles"
                :key="index"
                class="tile"
                :class="{ selected: selectedTiles.includes(tile) }"
                @click="toggleTile(tile)"
              >
                {{ tile }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Judging Phase -->
    <div v-else-if="gameStore.phase === 'round_judging'" class="phase-content">
      <div class="prompt-card">
        <h2>{{ gameStore.currentRound?.prompt.text }}</h2>
      </div>

      <div v-if="gameStore.isJudge" class="judging-area">
        <p class="instruction">Pick the best answer:</p>

        <div class="submissions-list">
          <button
            v-for="submission in gameStore.currentRound?.submissions"
            :key="submission.player_id"
            class="submission-card"
            @click="handleSelectWinner(submission.player_id)"
            :disabled="gameStore.isLoading"
          >
            {{ submission.response_text }}
          </button>
        </div>
      </div>

      <div v-else class="waiting-message">
        <p>{{ gameStore.judge?.nickname }} is choosing the winner...</p>

        <div class="submissions-list readonly">
          <div
            v-for="submission in gameStore.currentRound?.submissions"
            :key="submission.player_id"
            class="submission-card readonly"
          >
            {{ submission.response_text }}
          </div>
        </div>
      </div>
    </div>

    <!-- Results Phase -->
    <div v-else-if="gameStore.phase === 'round_results'" class="phase-content">
      <div class="results-area">
        <!-- Overrule Voting Section (when judge picked self and not yet resolved) -->
        <div
          v-if="gameStore.judgePickedSelf && !gameStore.isOverruled && gameStore.roundWinner"
          class="overrule-section"
        >
          <h2>Judge picked their own answer!</h2>
          <div class="winner-card self-pick">
            <p class="winner-name">{{ gameStore.roundWinner.nickname }} (Judge)</p>
            <p class="winner-answer">
              {{
                gameStore.currentRound?.submissions.find(
                  (s) => s.player_id === gameStore.currentRound?.winner_id,
                )?.response_text
              }}
            </p>
          </div>

          <div v-if="gameStore.canOverruleVote" class="voting-area">
            <p class="vote-prompt">Do you want to overrule this decision?</p>
            <p class="vote-note">(Requires unanimous vote from all non-judges)</p>
            <div class="vote-buttons">
              <button
                class="vote-btn overrule"
                @click="handleOverruleVote(true)"
                :disabled="gameStore.isLoading"
              >
                Overrule
              </button>
              <button
                class="vote-btn keep"
                @click="handleOverruleVote(false)"
                :disabled="gameStore.isLoading"
              >
                Keep Winner
              </button>
            </div>
          </div>

          <div v-else-if="gameStore.hasCastOverruleVote" class="waiting-message">
            <p>You voted. Waiting for others...</p>
          </div>

          <div v-else-if="gameStore.isJudge" class="waiting-message">
            <p>Other players are voting on whether to overrule your choice...</p>
          </div>

          <!-- Voting progress visible to all players -->
          <div v-if="overruleVoteProgress" class="vote-progress">
            <p class="vote-progress-title">Overrule Vote Progress</p>
            <div class="vote-progress-bar">
              <div
                class="vote-progress-fill for"
                :style="{
                  width: `${(overruleVoteProgress.votesFor / overruleVoteProgress.totalVoters) * 100}%`,
                }"
              ></div>
              <div
                class="vote-progress-fill against"
                :style="{
                  width: `${(overruleVoteProgress.votesAgainst / overruleVoteProgress.totalVoters) * 100}%`,
                  left: `${(overruleVoteProgress.votesFor / overruleVoteProgress.totalVoters) * 100}%`,
                }"
              ></div>
            </div>
            <div class="vote-progress-labels">
              <span class="for-label">{{ overruleVoteProgress.votesFor }} for overrule</span>
              <span class="against-label">{{ overruleVoteProgress.votesAgainst }} against</span>
              <span class="pending-label"
                >{{
                  overruleVoteProgress.totalVoters - overruleVoteProgress.totalVoted
                }}
                pending</span
              >
            </div>
            <p class="vote-progress-note">Requires unanimous vote to overrule</p>
          </div>
        </div>

        <!-- Winner Voting Section (after successful overrule) -->
        <div
          v-else-if="gameStore.isOverruled && !gameStore.roundWinner"
          class="winner-voting-section"
        >
          <h2>Overruled! Vote for a new winner</h2>
          <div class="prompt-reminder">
            <p>Prompt: {{ gameStore.currentRound?.prompt.text }}</p>
          </div>

          <div v-if="gameStore.canWinnerVote" class="voting-area">
            <p class="vote-prompt">Choose the best answer:</p>
            <div class="submissions-list">
              <button
                v-for="submission in gameStore.currentRound?.submissions.filter(
                  (s) => s.player_id !== gameStore.currentRound?.judge_id,
                )"
                :key="submission.player_id"
                class="submission-card vote-option"
                @click="handleWinnerVote(submission.player_id)"
                :disabled="gameStore.isLoading"
              >
                <span class="submission-text">{{ submission.response_text }}</span>
                <span class="submission-author"
                  >- {{ getPlayerNickname(submission.player_id) }}</span
                >
              </button>
            </div>
          </div>

          <div v-else-if="gameStore.hasCastWinnerVote" class="waiting-message">
            <p>
              You voted. Waiting for others... ({{ gameStore.winnerVoteCount }}/{{
                gameStore.players.length - 1
              }})
            </p>
          </div>

          <div v-else-if="gameStore.isJudge" class="waiting-message">
            <p>Other players are voting for a new winner...</p>
          </div>
        </div>

        <!-- Normal Winner Display -->
        <div v-else>
          <h2>Winner!</h2>
          <div class="winner-card" :class="{ 'was-overruled': gameStore.isOverruled }">
            <p class="winner-name">{{ gameStore.roundWinner?.nickname }}</p>
            <p class="winner-answer">
              {{
                gameStore.currentRound?.submissions.find(
                  (s) => s.player_id === gameStore.currentRound?.winner_id,
                )?.response_text
              }}
            </p>
            <p v-if="gameStore.isOverruled" class="overrule-note">Chosen by player vote</p>
          </div>
        </div>

        <div class="all-submissions">
          <h3>All Answers</h3>
          <div
            v-for="submission in gameStore.currentRound?.submissions"
            :key="submission.player_id"
            class="submission-result"
            :class="{
              winner: submission.player_id === gameStore.currentRound?.winner_id,
              'judge-self-pick':
                gameStore.judgePickedSelf &&
                submission.player_id === gameStore.currentRound?.judge_id,
            }"
          >
            <span class="player-name">{{ getPlayerNickname(submission.player_id) }}:</span>
            <span class="answer">{{ submission.response_text }}</span>
            <span
              v-if="submission.player_id === gameStore.currentRound?.judge_id"
              class="judge-badge"
              >(Judge)</span
            >
          </div>
        </div>

        <button
          v-if="gameStore.isHost && gameStore.roundWinner"
          class="advance-btn"
          @click="handleAdvance"
          :disabled="gameStore.isLoading"
        >
          {{ gameStore.isLoading ? 'Loading...' : 'Next Round' }}
        </button>
        <p v-else-if="!gameStore.roundWinner" class="waiting-text">
          Waiting for voting to complete...
        </p>
        <p v-else class="waiting-text">Waiting for host to start next round...</p>
      </div>
    </div>

    <!-- Game Over -->
    <div v-else-if="gameStore.phase === 'game_over'" class="phase-content">
      <div class="game-over">
        <h1>Game Over!</h1>
        <div class="final-scores">
          <div
            v-for="player in [...gameStore.players].sort((a, b) => b.score - a.score)"
            :key="player.id"
            class="final-score"
            :class="{ winner: player.score >= (gameStore.config?.points_to_win ?? 5) }"
          >
            <span class="rank">{{
              player.score >= (gameStore.config?.points_to_win ?? 5) ? 'Winner!' : ''
            }}</span>
            <span class="name">{{ player.nickname }}</span>
            <span class="score">{{ player.score }} points</span>
          </div>
        </div>
        <button class="leave-btn" @click="leaveGame">Back to Home</button>
      </div>
    </div>

    <button class="leave-game-btn" @click="leaveGame">Leave Game</button>
  </main>
</template>

<style scoped>
.game {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
  min-height: 100vh;
  animation: fadeInUp 0.4s var(--animation-smooth);
}

@media (min-width: 1024px) {
  .game {
    max-width: 1200px;
    padding: 1.5rem;
  }
}

@media (min-width: 1280px) {
  .game {
    max-width: 1400px;
  }
}

@media (min-width: 1536px) {
  .game {
    max-width: 1600px;
  }
}

.game-header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  margin-bottom: 1rem;
}

@media (min-width: 640px) {
  .game-header {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.round-info {
  font-family: var(--font-mono);
  font-size: clamp(1rem, 3vw, 1.3rem);
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: center;
}

@media (min-width: 640px) {
  .round-info {
    text-align: left;
  }
}

.scores {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

@media (min-width: 640px) {
  .scores {
    justify-content: flex-end;
    gap: 0.75rem;
  }
}

@media (min-width: 1024px) {
  .scores {
    gap: 1rem;
  }
}

.player-score {
  font-family: var(--font-mono);
  padding: 0.25rem 0.5rem;
  background: var(--color-background);
  border-radius: 4px;
  font-size: clamp(0.75rem, 2vw, 0.9rem);
  border: 1px solid var(--color-border);
}

.player-score.is-you {
  background: var(--accent-primary);
  color: var(--paper-light);
  border-color: var(--accent-primary);
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

.phase-content {
  padding: 0.5rem;
}

@media (min-width: 640px) {
  .phase-content {
    padding: 1rem;
  }
}

.prompt-card {
  background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-primary-hover) 100%);
  color: var(--paper-light);
  padding: 1.5rem;
  border-radius: 12px;
  text-align: center;
  margin-bottom: 1.5rem;
  border: 2px solid var(--accent-primary-hover);
}

@media (min-width: 640px) {
  .prompt-card {
    padding: 2rem;
  }
}

@media (min-width: 1024px) {
  .prompt-card {
    padding: 2.5rem 3rem;
  }
}

.prompt-card h2 {
  font-size: clamp(1.2rem, 4vw, 1.75rem);
  margin-bottom: 0.5rem;
  line-height: 1.3;
}

.judge-info {
  font-family: var(--font-mono);
  opacity: 0.9;
  font-size: clamp(0.8rem, 2.5vw, 0.95rem);
}

.waiting-message {
  font-family: var(--font-mono);
  text-align: center;
  padding: 1.5rem;
  background: var(--color-background-soft);
  border-radius: 8px;
}

@media (min-width: 640px) {
  .waiting-message {
    padding: 2rem;
  }
}

/* Submission layout - split view on large screens */
.submission-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media (min-width: 1024px) {
  .submission-layout {
    flex-direction: row;
    gap: 2rem;
  }

  .submission-controls {
    flex: 1;
    min-width: 0;
  }

  .tiles-section {
    flex: 2;
    min-width: 0;
  }
}

@media (min-width: 1280px) {
  .submission-layout {
    gap: 2.5rem;
  }
}

.submission-controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (min-width: 1024px) {
  .submission-controls {
    position: sticky;
    top: 1rem;
    align-self: flex-start;
  }

  .submission-controls .submit-btn {
    max-width: none;
  }
}

.instruction {
  font-family: var(--font-mono);
  margin-bottom: 1rem;
  font-weight: 500;
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.03em;
}

@media (min-width: 1024px) {
  .instruction {
    margin-bottom: 0;
  }
}

.selected-preview {
  background: var(--card-bg);
  padding: 1.25rem;
  border-radius: 4px;
  min-height: 60px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed var(--card-border);
  box-shadow: inset 0 2px 4px var(--tile-shadow);
}

@media (min-width: 640px) {
  .selected-preview {
    padding: 1.5rem;
    min-height: 70px;
  }
}

.placeholder {
  opacity: 0.5;
  font-style: italic;
  font-family: var(--font-mono);
  font-size: clamp(0.85rem, 2.5vw, 1rem);
}

.preview-text {
  font-size: clamp(1rem, 3vw, 1.2rem);
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--ink-dark);
  text-transform: lowercase;
  line-height: 1.4;
}

.tiles-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  background: var(--paper-mute);
  border-radius: 8px;
  box-shadow: inset 0 2px 8px var(--tile-shadow);
  justify-content: center;
  border: 1px solid var(--paper-dark);
}

@media (min-width: 640px) {
  .tiles-grid {
    gap: 0.5rem;
    padding: 1rem;
    justify-content: flex-start;
  }
}

@media (min-width: 1024px) {
  .tiles-grid {
    gap: 0.6rem;
    padding: 1.25rem;
  }
}

.tile {
  padding: 0.35rem 0.5rem;
  /* Always white background with black text for readability */
  background: #ffffff;
  color: #1a1814;
  border: 1px solid #c4b8a4;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: clamp(0.8rem, 2.5vw, 0.95rem);
  box-shadow:
    1px 1px 2px rgba(45, 42, 36, 0.15),
    inset 0 0 0 1px rgba(255, 255, 255, 0.5);
  text-transform: lowercase;
}

@media (min-width: 640px) {
  .tile {
    padding: 0.4rem 0.6rem;
  }
}

@media (min-width: 1024px) {
  .tile {
    padding: 0.5rem 0.75rem;
    font-size: 1rem;
  }
}

.tile:hover {
  transform: scale(1.05) rotate(-1deg);
  box-shadow:
    2px 2px 4px rgba(45, 42, 36, 0.2),
    inset 0 0 0 1px rgba(255, 255, 255, 0.5);
}

.tile.selected {
  /* Selected tiles: dark background with white text */
  background: #2d2a24;
  color: #ffffff;
  border-color: #1a1814;
  transform: scale(1.05);
  box-shadow:
    2px 2px 4px rgba(45, 42, 36, 0.25),
    inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.submit-btn {
  width: 100%;
  padding: 1rem;
  background: var(--accent-primary);
  color: var(--paper-light);
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.submit-btn:hover:not(:disabled) {
  background: var(--accent-primary-hover);
}

@media (min-width: 640px) {
  .submit-btn {
    max-width: 300px;
    margin: 0 auto;
    display: block;
  }
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.judging-area {
  text-align: center;
}

.submissions-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}

@media (min-width: 768px) {
  .submissions-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
}

@media (min-width: 1024px) {
  .submissions-list {
    gap: 1.25rem;
  }
}

.submission-card {
  padding: 1.25rem;
  background: var(--card-bg);
  border: 2px solid var(--card-border);
  border-radius: 4px;
  font-size: clamp(1rem, 3vw, 1.15rem);
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--ink-dark);
  text-transform: lowercase;
  box-shadow: 2px 2px 4px var(--tile-shadow);
}

@media (min-width: 640px) {
  .submission-card {
    padding: 1.5rem;
  }
}

.submission-card:hover:not(.readonly) {
  border-color: var(--accent-primary);
  transform: scale(1.02) rotate(-0.5deg);
  box-shadow: 3px 3px 6px var(--tile-shadow);
}

.submission-card.readonly {
  cursor: default;
}

.results-area {
  text-align: center;
}

.results-area h2 {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: clamp(1.25rem, 4vw, 1.75rem);
}

.winner-card {
  background: linear-gradient(135deg, var(--accent-tertiary) 0%, var(--accent-secondary) 100%);
  padding: 1.5rem;
  border-radius: 12px;
  margin: 1rem 0;
  border: 2px solid var(--accent-secondary);
}

@media (min-width: 640px) {
  .winner-card {
    padding: 2rem;
    max-width: 600px;
    margin: 1rem auto;
  }
}

.winner-name {
  font-family: var(--font-mono);
  font-size: clamp(1.25rem, 4vw, 1.5rem);
  font-weight: bold;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.winner-answer {
  font-size: clamp(1rem, 3vw, 1.25rem);
  font-family: var(--font-mono);
  font-weight: 600;
  text-transform: lowercase;
}

.all-submissions {
  margin: 2rem 0;
}

.all-submissions h3 {
  margin-bottom: 1rem;
  text-transform: uppercase;
  font-size: 1rem;
  letter-spacing: 0.03em;
}

.submission-result {
  padding: 0.75rem 1rem;
  background: var(--card-bg);
  border: 1px solid var(--paper-dark);
  border-radius: 4px;
  margin-bottom: 0.5rem;
  text-align: left;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.submission-result .answer {
  font-family: var(--font-mono);
  font-weight: 600;
  text-transform: lowercase;
}

.submission-result.winner {
  background: var(--paper);
  border: 2px solid var(--accent-tertiary);
}

.player-name {
  font-family: var(--font-mono);
  font-weight: 600;
}

.advance-btn {
  padding: 1rem 2rem;
  background: var(--accent-primary);
  color: var(--paper-light);
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.advance-btn:hover:not(:disabled) {
  background: var(--accent-primary-hover);
}

.advance-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.waiting-text {
  font-family: var(--font-mono);
  opacity: 0.7;
  font-style: italic;
}

.game-over {
  text-align: center;
  padding: 1.5rem;
}

@media (min-width: 640px) {
  .game-over {
    padding: 2rem;
  }
}

.game-over h1 {
  font-size: clamp(2rem, 6vw, 3rem);
  margin-bottom: 2rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.final-scores {
  margin-bottom: 2rem;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.final-score {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  margin-bottom: 0.5rem;
  font-family: var(--font-mono);
}

.final-score .name {
  font-weight: 600;
}

.final-score .score {
  font-weight: 600;
}

.final-score .rank {
  font-size: 0.85rem;
  text-transform: uppercase;
}

.final-score.winner {
  background: linear-gradient(135deg, var(--accent-tertiary) 0%, var(--accent-secondary) 100%);
}

.leave-btn {
  padding: 1rem 2rem;
  background: var(--color-text);
  color: var(--color-background);
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.leave-game-btn {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  padding: 0.5rem 1rem;
  background: var(--color-danger);
  color: var(--paper-light);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  z-index: 100;
}

.leave-game-btn:hover {
  background: var(--color-danger-hover);
}

/* Overrule voting styles */
.overrule-section,
.winner-voting-section {
  text-align: center;
}

.overrule-section h2,
.winner-voting-section h2 {
  font-size: clamp(1.1rem, 3.5vw, 1.5rem);
}

.winner-card.self-pick {
  background: linear-gradient(135deg, var(--color-warning) 0%, var(--accent-secondary) 100%);
}

.winner-card.was-overruled {
  background: linear-gradient(135deg, var(--color-success) 0%, var(--color-success-hover) 100%);
}

.overrule-note {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  opacity: 0.9;
  margin-top: 0.5rem;
  font-style: italic;
}

.voting-area {
  margin: 1.5rem 0;
  padding: 1.25rem;
  background: var(--color-background-soft);
  border-radius: 8px;
}

@media (min-width: 640px) {
  .voting-area {
    padding: 1.5rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
  }
}

.vote-prompt {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.vote-note {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  opacity: 0.7;
  margin-bottom: 1rem;
}

.vote-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

@media (min-width: 480px) {
  .vote-buttons {
    flex-direction: row;
    gap: 1rem;
    justify-content: center;
  }
}

.vote-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: transform 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

@media (min-width: 480px) {
  .vote-btn {
    min-width: 140px;
  }
}

.vote-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.vote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.vote-btn.overrule {
  background: var(--color-danger);
  color: var(--paper-light);
}

.vote-btn.overrule:hover:not(:disabled) {
  background: var(--color-danger-hover);
}

.vote-btn.keep {
  background: var(--color-success);
  color: var(--paper-light);
}

.vote-btn.keep:hover:not(:disabled) {
  background: var(--color-success-hover);
}

.prompt-reminder {
  font-family: var(--font-mono);
  background: var(--color-background-soft);
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
}

@media (min-width: 640px) {
  .prompt-reminder {
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
  }
}

.submission-card.vote-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.submission-author {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  opacity: 0.7;
}

.submission-result.judge-self-pick {
  border-left: 4px solid var(--color-warning);
}

.judge-badge {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: var(--color-warning);
  color: var(--ink-dark);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  margin-left: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

/* Timer and submission progress styles */
.submission-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  margin-bottom: 1rem;
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .submission-status {
    flex-direction: row;
    justify-content: space-between;
    padding: 1rem;
    gap: 1rem;
  }
}

.timer {
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: clamp(1.25rem, 4vw, 1.5rem);
  font-weight: bold;
  padding: 0.5rem 1rem;
  background: var(--color-background);
  border-radius: 8px;
  min-width: 100px;
  justify-content: center;
}

.timer.urgent {
  background: var(--color-danger-light);
  color: var(--color-danger);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.timer-icon {
  font-size: 1rem;
}

@media (min-width: 640px) {
  .timer-icon {
    font-size: 1.2rem;
  }
}

.progress-indicator {
  flex: 1;
  width: 100%;
  max-width: 100%;
}

@media (min-width: 640px) {
  .progress-indicator {
    max-width: 300px;
  }
}

@media (min-width: 1024px) {
  .progress-indicator {
    max-width: 400px;
  }
}

.progress-text {
  font-family: var(--font-mono);
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  text-align: center;
  font-size: 0.85rem;
}

.progress-bar {
  height: 10px;
  background: var(--color-background);
  border-radius: 5px;
  overflow: hidden;
}

@media (min-width: 640px) {
  .progress-bar {
    height: 12px;
    border-radius: 6px;
  }
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-primary-light));
  border-radius: 6px;
  transition: width 0.3s ease;
}

.progress-detail {
  font-family: var(--font-mono);
  margin-top: 0.5rem;
  font-size: 0.85rem;
  opacity: 0.8;
}

/* Vote progress styles */
.vote-progress {
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
}

@media (min-width: 640px) {
  .vote-progress {
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
  }
}

.vote-progress-title {
  font-family: var(--font-mono);
  font-weight: 600;
  margin-bottom: 0.75rem;
  text-align: center;
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.03em;
}

.vote-progress-bar {
  height: 20px;
  background: var(--color-background);
  border-radius: 10px;
  overflow: hidden;
  position: relative;
  margin-bottom: 0.5rem;
}

@media (min-width: 640px) {
  .vote-progress-bar {
    height: 24px;
    border-radius: 12px;
  }
}

.vote-progress-fill {
  height: 100%;
  position: absolute;
  top: 0;
  transition: width 0.3s ease;
}

.vote-progress-fill.for {
  background: linear-gradient(90deg, var(--color-danger), var(--color-danger-hover));
  left: 0;
}

.vote-progress-fill.against {
  background: linear-gradient(90deg, var(--color-success), var(--color-success-hover));
}

.vote-progress-labels {
  font-family: var(--font-mono);
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.for-label {
  color: var(--color-danger);
  font-weight: 600;
}

.against-label {
  color: var(--color-success);
  font-weight: 600;
}

.pending-label {
  opacity: 0.7;
}

.vote-progress-note {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-align: center;
  opacity: 0.7;
  margin-top: 0.5rem;
  font-style: italic;
}

/* Mobile Responsiveness - Bottom padding for fixed leave button */
@media (max-width: 640px) {
  .game {
    padding-bottom: 70px;
  }

  .leave-game-btn {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    border-radius: 0;
    padding: 1rem;
    font-size: 0.95rem;
  }
}
</style>
