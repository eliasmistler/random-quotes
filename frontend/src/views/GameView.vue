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
        <p class="instruction">Select tiles to create your answer:</p>

        <div class="selected-preview">
          <span v-if="selectedTiles.length === 0" class="placeholder">
            Click tiles below to build your answer
          </span>
          <span v-else class="preview-text">{{ selectedTiles.join(' ') }}</span>
        </div>

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

        <button
          class="submit-btn"
          :disabled="selectedTiles.length === 0 || gameStore.isLoading"
          @click="handleSubmit"
        >
          {{ gameStore.isLoading ? 'Submitting...' : 'Submit Answer' }}
        </button>
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
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
  min-height: 100vh;
}

.game-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  margin-bottom: 1rem;
}

.round-info {
  font-size: 1.2rem;
  font-weight: bold;
}

.scores {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.player-score {
  padding: 0.25rem 0.5rem;
  background: var(--color-background);
  border-radius: 4px;
  font-size: 0.9rem;
}

.player-score.is-you {
  background: #4caf50;
  color: white;
}

.error-message {
  background: #ffebee;
  color: #c62828;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.phase-content {
  padding: 1rem;
}

.prompt-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  border-radius: 12px;
  text-align: center;
  margin-bottom: 1.5rem;
}

.prompt-card h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

.judge-info {
  opacity: 0.9;
  font-size: 0.9rem;
}

.waiting-message {
  text-align: center;
  padding: 2rem;
  background: var(--color-background-soft);
  border-radius: 8px;
}

.instruction {
  margin-bottom: 1rem;
  font-weight: 500;
}

.selected-preview {
  background: #f5f5dc;
  padding: 1.5rem;
  border-radius: 4px;
  min-height: 70px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #8b7355;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.placeholder {
  opacity: 0.5;
  font-style: italic;
  font-family: 'Courier New', Courier, monospace;
}

.preview-text {
  font-size: 1.1rem;
  font-weight: 600;
  font-family: 'Courier New', Courier, monospace;
  color: #1a1a1a;
  text-transform: lowercase;
}

.tiles-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #d4c4a8;
  border-radius: 8px;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.15);
}

.tile {
  padding: 0.4rem 0.6rem;
  background: #ffffff;
  color: #1a1a1a;
  border: 1px solid #ccc;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: 'Courier New', Courier, monospace;
  font-weight: 600;
  font-size: 0.95rem;
  box-shadow:
    1px 1px 2px rgba(0, 0, 0, 0.15),
    inset 0 0 0 1px rgba(255, 255, 255, 0.5);
  text-transform: lowercase;
}

.tile:hover {
  transform: scale(1.05) rotate(-1deg);
  box-shadow:
    2px 2px 4px rgba(0, 0, 0, 0.2),
    inset 0 0 0 1px rgba(255, 255, 255, 0.5);
}

.tile.selected {
  background: #2d2d2d;
  color: #ffffff;
  border-color: #1a1a1a;
  transform: scale(1.05);
  box-shadow:
    2px 2px 4px rgba(0, 0, 0, 0.3),
    inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.submit-btn {
  width: 100%;
  padding: 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.judging-area {
  text-align: center;
}

.submissions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.submission-card {
  padding: 1.5rem;
  background: #f5f5dc;
  border: 2px solid #8b7355;
  border-radius: 4px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'Courier New', Courier, monospace;
  font-weight: 600;
  color: #1a1a1a;
  text-transform: lowercase;
  box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.15);
}

.submission-card:hover:not(.readonly) {
  border-color: #5d4e37;
  transform: scale(1.02) rotate(-0.5deg);
  box-shadow: 3px 3px 6px rgba(0, 0, 0, 0.2);
}

.submission-card.readonly {
  cursor: default;
}

.results-area {
  text-align: center;
}

.winner-card {
  background: linear-gradient(135deg, #ffd700 0%, #ffb347 100%);
  padding: 2rem;
  border-radius: 12px;
  margin: 1rem 0;
}

.winner-name {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.winner-answer {
  font-size: 1.2rem;
  font-family: 'Courier New', Courier, monospace;
  font-weight: 600;
  text-transform: lowercase;
}

.all-submissions {
  margin: 2rem 0;
}

.all-submissions h3 {
  margin-bottom: 1rem;
}

.submission-result {
  padding: 0.75rem;
  background: #f5f5dc;
  border: 1px solid #d4c4a8;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  text-align: left;
}

.submission-result .answer {
  font-family: 'Courier New', Courier, monospace;
  font-weight: 600;
  text-transform: lowercase;
}

.submission-result.winner {
  background: #fff9c4;
  border: 2px solid #ffd700;
}

.player-name {
  font-weight: 500;
  margin-right: 0.5rem;
}

.advance-btn {
  padding: 1rem 2rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
}

.advance-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.waiting-text {
  opacity: 0.7;
  font-style: italic;
}

.game-over {
  text-align: center;
  padding: 2rem;
}

.game-over h1 {
  font-size: 2.5rem;
  margin-bottom: 2rem;
}

.final-scores {
  margin-bottom: 2rem;
}

.final-score {
  display: flex;
  justify-content: space-between;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  margin-bottom: 0.5rem;
}

.final-score.winner {
  background: linear-gradient(135deg, #ffd700 0%, #ffb347 100%);
}

.leave-btn {
  padding: 1rem 2rem;
  background: var(--color-text);
  color: var(--color-background);
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
}

.leave-game-btn {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  padding: 0.5rem 1rem;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

/* Overrule voting styles */
.overrule-section,
.winner-voting-section {
  text-align: center;
}

.winner-card.self-pick {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
}

.winner-card.was-overruled {
  background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);
}

.overrule-note {
  font-size: 0.9rem;
  opacity: 0.9;
  margin-top: 0.5rem;
  font-style: italic;
}

.voting-area {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--color-background-soft);
  border-radius: 8px;
}

.vote-prompt {
  font-size: 1.1rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.vote-note {
  font-size: 0.9rem;
  opacity: 0.7;
  margin-bottom: 1rem;
}

.vote-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.vote-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: transform 0.2s;
}

.vote-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.vote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.vote-btn.overrule {
  background: #dc3545;
  color: white;
}

.vote-btn.keep {
  background: #4caf50;
  color: white;
}

.prompt-reminder {
  background: var(--color-background-soft);
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
}

.submission-card.vote-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.submission-author {
  font-size: 0.9rem;
  opacity: 0.7;
}

.submission-result.judge-self-pick {
  border-left: 4px solid #ff9800;
}

.judge-badge {
  font-size: 0.8rem;
  background: #ff9800;
  color: white;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  margin-left: 0.5rem;
}

/* Timer and submission progress styles */
.submission-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  margin-bottom: 1rem;
  gap: 1rem;
}

.timer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.5rem;
  font-weight: bold;
  padding: 0.5rem 1rem;
  background: var(--color-background);
  border-radius: 8px;
  min-width: 100px;
  justify-content: center;
}

.timer.urgent {
  background: #ffebee;
  color: #c62828;
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
  font-size: 1.2rem;
}

.progress-indicator {
  flex: 1;
  max-width: 300px;
}

.progress-text {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  text-align: center;
}

.progress-bar {
  height: 12px;
  background: var(--color-background);
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #8bc34a);
  border-radius: 6px;
  transition: width 0.3s ease;
}

.progress-detail {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  opacity: 0.8;
}

/* Vote progress styles */
.vote-progress {
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--color-background-soft);
  border-radius: 8px;
}

.vote-progress-title {
  font-weight: 600;
  margin-bottom: 0.75rem;
  text-align: center;
}

.vote-progress-bar {
  height: 24px;
  background: var(--color-background);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  margin-bottom: 0.5rem;
}

.vote-progress-fill {
  height: 100%;
  position: absolute;
  top: 0;
  transition: width 0.3s ease;
}

.vote-progress-fill.for {
  background: linear-gradient(90deg, #dc3545, #e57373);
  left: 0;
}

.vote-progress-fill.against {
  background: linear-gradient(90deg, #4caf50, #81c784);
}

.vote-progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.for-label {
  color: #dc3545;
  font-weight: 500;
}

.against-label {
  color: #4caf50;
  font-weight: 500;
}

.pending-label {
  opacity: 0.7;
}

.vote-progress-note {
  font-size: 0.8rem;
  text-align: center;
  opacity: 0.7;
  margin-top: 0.5rem;
  font-style: italic;
}
</style>
