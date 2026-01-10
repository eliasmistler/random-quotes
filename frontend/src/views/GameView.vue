<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'

const router = useRouter()
const gameStore = useGameStore()

const pollingInterval = ref<number | null>(null)
const selectedTiles = ref<string[]>([])

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
        <p class="judge-info">Judge: {{ gameStore.judge?.nickname }}</p>
      </div>

      <div v-if="gameStore.isJudge" class="waiting-message">
        <p>You are the judge this round. Wait for other players to submit their answers.</p>
      </div>

      <div v-else-if="gameStore.hasSubmitted" class="waiting-message">
        <p>Response submitted! Waiting for other players...</p>
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
        <h2>Winner!</h2>
        <div class="winner-card">
          <p class="winner-name">{{ gameStore.roundWinner?.nickname }}</p>
          <p class="winner-answer">
            {{
              gameStore.currentRound?.submissions.find(
                (s) => s.player_id === gameStore.currentRound?.winner_id,
              )?.response_text
            }}
          </p>
        </div>

        <div class="all-submissions">
          <h3>All Answers</h3>
          <div
            v-for="submission in gameStore.currentRound?.submissions"
            :key="submission.player_id"
            class="submission-result"
            :class="{ winner: submission.player_id === gameStore.currentRound?.winner_id }"
          >
            <span class="player-name">{{ getPlayerNickname(submission.player_id) }}:</span>
            <span class="answer">{{ submission.response_text }}</span>
          </div>
        </div>

        <button
          v-if="gameStore.isHost"
          class="advance-btn"
          @click="handleAdvance"
          :disabled="gameStore.isLoading"
        >
          {{ gameStore.isLoading ? 'Loading...' : 'Next Round' }}
        </button>
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
            <span class="rank">{{ player.score >= (gameStore.config?.points_to_win ?? 5) ? 'Winner!' : '' }}</span>
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
  background: var(--color-background-soft);
  padding: 1rem;
  border-radius: 8px;
  min-height: 60px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder {
  opacity: 0.5;
  font-style: italic;
}

.preview-text {
  font-size: 1.2rem;
  font-weight: 500;
}

.tiles-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tile {
  padding: 0.5rem 0.75rem;
  background: var(--color-background-soft);
  border: 2px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.tile:hover {
  border-color: #667eea;
}

.tile.selected {
  background: #667eea;
  color: white;
  border-color: #667eea;
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
  background: var(--color-background-soft);
  border: 2px solid var(--color-border);
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.submission-card:hover:not(.readonly) {
  border-color: #667eea;
  transform: scale(1.02);
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
}

.all-submissions {
  margin: 2rem 0;
}

.all-submissions h3 {
  margin-bottom: 1rem;
}

.submission-result {
  padding: 0.75rem;
  background: var(--color-background-soft);
  border-radius: 4px;
  margin-bottom: 0.5rem;
  text-align: left;
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
</style>
