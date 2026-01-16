<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import ChatWindow from '@/components/ChatWindow.vue'

const router = useRouter()
const gameStore = useGameStore()

const timerInterval = ref<number | null>(null)
const remainingSeconds = ref<number | null>(null)

// Multi-row answer box (up to 5 rows)
const MAX_ROWS = 5
const answerRows = ref<string[][]>([[], [], [], [], []])
const draggedTile = ref<string | null>(null)
const dragSource = ref<{ type: 'pool' | 'answer'; row?: number; index?: number } | null>(null)
const dropTargetRow = ref<number | null>(null)

// Computed: all selected tiles flattened (for submission)
const selectedTiles = computed(() => answerRows.value.flat())

// Computed: which tiles are in the answer box
const tilesInAnswer = computed(() => new Set(selectedTiles.value))

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

// Check if current player won the game
const isCurrentPlayerWinner = computed(() => {
  const pointsToWin = gameStore.config?.points_to_win ?? 5
  const currentPlayer = gameStore.players.find((p) => p.id === gameStore.playerId)
  return currentPlayer ? currentPlayer.score >= pointsToWin : false
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

// Click to toggle tile (fallback for non-drag interaction)
function toggleTile(tile: string) {
  // If tile is in answer box, remove it
  for (let i = 0; i < MAX_ROWS; i++) {
    const row = answerRows.value[i]
    if (!row) continue
    const idx = row.indexOf(tile)
    if (idx !== -1) {
      row.splice(idx, 1)
      return
    }
  }
  // Otherwise add it to first row with space
  answerRows.value[0]?.push(tile)
}

// Drag start from the tiles pool
function handleDragStart(e: DragEvent, tile: string) {
  draggedTile.value = tile
  dragSource.value = { type: 'pool' }
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', tile)
  }
}

// Drag start from within the answer box
function handleAnswerDragStart(e: DragEvent, tile: string, rowIndex: number, tileIndex: number) {
  draggedTile.value = tile
  dragSource.value = { type: 'answer', row: rowIndex, index: tileIndex }
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', tile)
  }
}

function handleDragEnd() {
  draggedTile.value = null
  dragSource.value = null
  dropTargetRow.value = null
}

function handleDragOver(e: DragEvent, rowIndex: number) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  dropTargetRow.value = rowIndex
}

function handleDragLeave(e: DragEvent, rowIndex: number) {
  if (dropTargetRow.value === rowIndex) {
    dropTargetRow.value = null
  }
}

function handleDrop(e: DragEvent, rowIndex: number) {
  e.preventDefault()
  const tile = draggedTile.value
  if (!tile) return

  // Remove from source if from answer box
  if (dragSource.value?.type === 'answer') {
    const srcRow = dragSource.value.row!
    const srcIndex = dragSource.value.index!
    answerRows.value[srcRow]?.splice(srcIndex, 1)
  }

  // Add to target row
  answerRows.value[rowIndex]?.push(tile)

  handleDragEnd()
}

function handleDropOnPool(e: DragEvent) {
  e.preventDefault()
  if (!draggedTile.value || dragSource.value?.type !== 'answer') return

  // Remove tile from answer area (return to pool)
  const srcRow = dragSource.value.row!
  const srcIndex = dragSource.value.index!
  answerRows.value[srcRow]?.splice(srcIndex, 1)

  handleDragEnd()
}

function removeTileFromAnswer(rowIndex: number, tileIndex: number) {
  answerRows.value[rowIndex]?.splice(tileIndex, 1)
}

function clearAnswer() {
  answerRows.value = [[], [], [], [], []]
}

// Get a stable index for a tile based on its content (for consistent styling)
function getTileStyleIndex(tile: string): number {
  // Use a hash of the tile content for consistent styling
  let hash = 0
  for (let i = 0; i < tile.length; i++) {
    hash = ((hash << 5) - hash) + tile.charCodeAt(i)
    hash = hash & hash
  }
  return Math.abs(hash) % 14 + 1 // 1-14 for nth-child patterns
}

async function handleSubmit() {
  if (selectedTiles.value.length === 0) return

  try {
    await gameStore.submitResponse(selectedTiles.value)
    answerRows.value = [[], [], [], [], []]
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

async function handlePlayAgain() {
  try {
    await gameStore.restartGame()
  } catch (e) {
    console.error('Failed to restart game:', e)
  }
}

function getPlayerNickname(playerId: string): string {
  return gameStore.players.find((p) => p.id === playerId)?.nickname ?? 'Unknown'
}
</script>

<template>
  <main class="game">
    <!-- Game Header -->
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
      <!-- Prompt Card - Paper note style -->
      <div class="prompt-card">
        <div class="tape-strip"></div>
        <h2>{{ gameStore.currentRound?.prompt.text }}</h2>
        <p class="judge-info">Judge will be selected after submissions</p>
      </div>

      <!-- Timer and Progress -->
      <div class="submission-status">
        <div class="timer" :class="{ urgent: timerUrgent }">
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

      <!-- Already submitted state -->
      <div v-if="gameStore.hasSubmitted" class="waiting-message">
        <p>Response submitted!</p>
        <p class="progress-detail">Waiting for other players...</p>
      </div>

      <!-- Submission area -->
      <div v-else class="submission-area">
        <div class="submission-layout">
          <!-- Controls panel -->
          <div class="submission-controls">
            <p class="instruction">Build your answer:</p>
            <p class="instruction-hint">Drag tiles into rows below (up to 5 rows)</p>

            <!-- Multi-row answer box -->
            <div class="answer-box" :class="{ 'has-content': selectedTiles.length > 0 }">
              <div
                v-for="(row, rowIndex) in answerRows"
                :key="rowIndex"
                class="answer-row"
                :class="{
                  'drop-target': dropTargetRow === rowIndex,
                  empty: row.length === 0,
                }"
                @dragover="handleDragOver($event, rowIndex)"
                @dragleave="handleDragLeave($event, rowIndex)"
                @drop="handleDrop($event, rowIndex)"
              >
                <template v-if="row.length === 0">
                  <span v-if="rowIndex === 0 && selectedTiles.length === 0" class="placeholder">
                    Drag tiles here to build your answer
                  </span>
                  <span v-else class="row-placeholder">Row {{ rowIndex + 1 }}</span>
                </template>
                <template v-else>
                  <span
                    v-for="(tile, tileIndex) in row"
                    :key="`${rowIndex}-${tileIndex}-${tile}`"
                    class="tile answer-tile"
                    :class="'tile-style-' + getTileStyleIndex(tile)"
                    draggable="true"
                    @dragstart="handleAnswerDragStart($event, tile, rowIndex, tileIndex)"
                    @dragend="handleDragEnd"
                    @click="removeTileFromAnswer(rowIndex, tileIndex)"
                  >{{ tile }}</span>
                </template>
              </div>
              <button
                v-if="selectedTiles.length > 0"
                class="clear-btn"
                @click="clearAnswer"
                title="Clear all"
              >
                Clear
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

          <!-- Tiles grid -->
          <div
            class="tiles-section"
            @dragover.prevent
            @drop="handleDropOnPool($event)"
          >
            <div class="tiles-grid">
              <button
                v-for="(tile, index) in gameStore.myTiles"
                :key="tile + '-' + index"
                class="tile"
                :class="[
                  'tile-style-' + getTileStyleIndex(tile),
                  {
                    selected: tilesInAnswer.has(tile),
                    dragging: draggedTile === tile
                  }
                ]"
                :draggable="!tilesInAnswer.has(tile)"
                @click="toggleTile(tile)"
                @dragstart="!tilesInAnswer.has(tile) && handleDragStart($event, tile)"
                @dragend="handleDragEnd"
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
        <div class="tape-strip"></div>
        <h2>{{ gameStore.currentRound?.prompt.text }}</h2>
      </div>

      <div v-if="gameStore.isJudge" class="judging-area">
        <p class="instruction">Pick the best answer:</p>

        <div class="submissions-list">
          <button
            v-for="submission in gameStore.currentRound?.submissions"
            :key="submission.player_id"
            class="submission-card submission-with-tiles"
            @click="handleSelectWinner(submission.player_id)"
            :disabled="gameStore.isLoading"
          >
            <div class="submission-tiles">
              <span
                v-for="(tile, tileIndex) in submission.tiles_used"
                :key="tileIndex"
                class="tile display-tile"
                :class="'tile-style-' + getTileStyleIndex(tile)"
              >{{ tile }}</span>
            </div>
          </button>
        </div>
      </div>

      <div v-else class="waiting-message">
        <p><strong>{{ gameStore.judge?.nickname }}</strong> is choosing the winner...</p>

        <div class="submissions-list readonly">
          <div
            v-for="submission in gameStore.currentRound?.submissions"
            :key="submission.player_id"
            class="submission-card submission-with-tiles readonly"
          >
            <div class="submission-tiles">
              <span
                v-for="(tile, tileIndex) in submission.tiles_used"
                :key="tileIndex"
                class="tile display-tile"
                :class="'tile-style-' + getTileStyleIndex(tile)"
              >{{ tile }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Results Phase -->
    <div v-else-if="gameStore.phase === 'round_results'" class="phase-content">
      <div class="results-area">
        <!-- Overrule Voting Section -->
        <div
          v-if="gameStore.judgePickedSelf && !gameStore.isOverruled && gameStore.roundWinner"
          class="overrule-section"
        >
          <h2>Judge picked their own answer!</h2>
          <div class="winner-card self-pick">
            <p class="winner-name">{{ gameStore.roundWinner.nickname }} (Judge)</p>
            <div class="winner-answer-tiles">
              <span
                v-for="(tile, tileIndex) in gameStore.currentRound?.submissions.find(
                  (s) => s.player_id === gameStore.currentRound?.winner_id,
                )?.tiles_used ?? []"
                :key="tileIndex"
                class="tile display-tile"
                :class="'tile-style-' + getTileStyleIndex(tile)"
              >{{ tile }}</span>
            </div>
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
            <p>Other players are voting on whether to overrule...</p>
          </div>

          <!-- Voting progress -->
          <div v-if="overruleVoteProgress" class="vote-progress">
            <p class="vote-progress-title">Vote Progress</p>
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
              <span class="for-label">{{ overruleVoteProgress.votesFor }} for</span>
              <span class="against-label">{{ overruleVoteProgress.votesAgainst }} against</span>
              <span class="pending-label">{{ overruleVoteProgress.totalVoters - overruleVoteProgress.totalVoted }} pending</span>
            </div>
          </div>
        </div>

        <!-- Winner Voting Section (after overrule) -->
        <div
          v-else-if="gameStore.isOverruled && !gameStore.roundWinner"
          class="winner-voting-section"
        >
          <h2>Overruled! Vote for a new winner</h2>
          <div class="prompt-reminder">
            <p>{{ gameStore.currentRound?.prompt.text }}</p>
          </div>

          <div v-if="gameStore.canWinnerVote" class="voting-area">
            <p class="vote-prompt">Choose the best answer:</p>
            <div class="submissions-list">
              <button
                v-for="submission in gameStore.currentRound?.submissions.filter(
                  (s) => s.player_id !== gameStore.currentRound?.judge_id,
                )"
                :key="submission.player_id"
                class="submission-card submission-with-tiles vote-option"
                @click="handleWinnerVote(submission.player_id)"
                :disabled="gameStore.isLoading"
              >
                <div class="submission-tiles">
                  <span
                    v-for="(tile, tileIndex) in submission.tiles_used"
                    :key="tileIndex"
                    class="tile display-tile"
                    :class="'tile-style-' + getTileStyleIndex(tile)"
                  >{{ tile }}</span>
                </div>
                <span class="submission-author">- {{ getPlayerNickname(submission.player_id) }}</span>
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
          <h2 v-if="gameStore.currentRound?.winner_id === gameStore.playerId" class="you-win">You Win This Round!</h2>
          <h2 v-else>Winner: {{ gameStore.roundWinner?.nickname }}</h2>
          <div class="winner-card" :class="{ 'was-overruled': gameStore.isOverruled, 'is-you': gameStore.currentRound?.winner_id === gameStore.playerId }">
            <div class="tape-strip"></div>
            <p class="winner-name" v-if="gameStore.currentRound?.winner_id !== gameStore.playerId">{{ gameStore.roundWinner?.nickname }}</p>
            <div class="winner-answer-tiles">
              <span
                v-for="(tile, tileIndex) in gameStore.currentRound?.submissions.find(
                  (s) => s.player_id === gameStore.currentRound?.winner_id,
                )?.tiles_used ?? []"
                :key="tileIndex"
                class="tile display-tile"
                :class="'tile-style-' + getTileStyleIndex(tile)"
              >{{ tile }}</span>
            </div>
            <p v-if="gameStore.isOverruled" class="overrule-note">Chosen by player vote</p>
          </div>
        </div>

        <!-- All Submissions -->
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
            <div class="answer-tiles-inline">
              <span
                v-for="(tile, tileIndex) in submission.tiles_used"
                :key="tileIndex"
                class="tile display-tile small"
                :class="'tile-style-' + getTileStyleIndex(tile)"
              >{{ tile }}</span>
            </div>
            <span
              v-if="submission.player_id === gameStore.currentRound?.judge_id"
              class="judge-badge"
            >(Judge)</span>
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
        <h1 v-if="isCurrentPlayerWinner" class="you-win-final">You Win!</h1>
        <h1 v-else class="you-lose-final">You Lose!</h1>
        <div class="final-scores">
          <div
            v-for="(player, index) in [...gameStore.players].sort((a, b) => b.score - a.score)"
            :key="player.id"
            class="final-score"
            :class="{
              winner: player.score >= (gameStore.config?.points_to_win ?? 5),
              'is-you': player.id === gameStore.playerId
            }"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <span class="rank">{{
              player.score >= (gameStore.config?.points_to_win ?? 5) ? '🏆' : ''
            }}</span>
            <span class="name">{{ player.nickname }}{{ player.id === gameStore.playerId ? ' (You)' : '' }}</span>
            <span class="score">{{ player.score }} pts</span>
          </div>
        </div>
        <div class="game-over-actions">
          <button v-if="gameStore.isHost" class="play-again-btn" @click="handlePlayAgain">
            Play Again
          </button>
          <button class="leave-btn" @click="leaveGame">Back to Home</button>
        </div>
      </div>
    </div>

    <!-- Chat Window -->
    <ChatWindow />

    <button class="leave-game-btn" @click="leaveGame">Leave Game</button>
  </main>
</template>

<style scoped>
.game {
  max-width: 1000px;
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

/* ==========================================================================
   GAME HEADER
   ========================================================================== */

.game-header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--scrap-newsprint);
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-paper);
}

@media (min-width: 640px) {
  .game-header {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.round-info {
  font-family: var(--font-headline-2);
  font-size: clamp(1.1rem, 3vw, 1.4rem);
  letter-spacing: 0.08em;
  text-align: center;
  color: var(--ink-black);
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
  }
}

.player-score {
  font-family: var(--font-typewriter);
  padding: 0.3rem 0.6rem;
  background: var(--scrap-white);
  font-size: 0.85rem;
  box-shadow: 1px 1px 2px rgba(0,0,0,0.1);
  color: var(--ink-black);
}

.player-score.is-you {
  background: var(--accent-red);
  color: white;
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
  border-left: 4px solid var(--color-danger);
  animation: shake 0.4s ease;
}

/* ==========================================================================
   PROMPT CARD - Key visual element
   ========================================================================== */

.prompt-card {
  background: var(--scrap-white);
  padding: 1.5rem;
  text-align: center;
  margin-bottom: 1.5rem;
  position: relative;
  box-shadow: var(--shadow-paper);
  transform: rotate(-0.3deg);
}

@media (min-width: 640px) {
  .prompt-card {
    padding: 2rem;
  }
}

.prompt-card .tape-strip {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%) rotate(-2deg);
  width: 70px;
  height: 22px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 200, 0.85) 0%,
    rgba(255, 255, 180, 0.7) 100%
  );
  box-shadow: inset 0 0 4px rgba(255, 255, 255, 0.5), 0 2px 4px rgba(0, 0, 0, 0.1);
}

.prompt-card h2 {
  font-family: var(--font-headline-3);
  font-size: clamp(1.2rem, 4vw, 1.75rem);
  margin-bottom: 0.5rem;
  line-height: 1.3;
  color: var(--ink-black);
  font-style: italic;
}

.judge-info {
  font-family: var(--font-typewriter);
  color: var(--ink-grey);
  font-size: 0.85rem;
}

/* ==========================================================================
   SUBMISSION STATUS (Timer + Progress)
   ========================================================================== */

.submission-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: var(--scrap-cream);
  margin-bottom: 1.5rem;
  gap: 0.75rem;
  box-shadow: var(--shadow-paper);
}

@media (min-width: 640px) {
  .submission-status {
    flex-direction: row;
    justify-content: space-between;
  }
}

.timer {
  font-family: var(--font-headline-2);
  font-size: 1.5rem;
  padding: 0.5rem 1rem;
  background: var(--scrap-white);
  box-shadow: var(--shadow-paper);
  min-width: 90px;
  text-align: center;
  color: var(--ink-black);
}

.timer.urgent {
  background: var(--color-danger);
  color: white;
  animation: pulse 1s infinite;
}

.progress-indicator {
  flex: 1;
  max-width: 350px;
  width: 100%;
}

.progress-text {
  font-family: var(--font-typewriter);
  display: block;
  margin-bottom: 0.5rem;
  text-align: center;
  font-size: 0.85rem;
}

.progress-bar {
  height: 10px;
  background: var(--scrap-white);
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
}

.progress-fill {
  height: 100%;
  background: var(--accent-red);
  transition: width 0.3s ease;
}

/* ==========================================================================
   WAITING MESSAGE
   ========================================================================== */

.waiting-message {
  font-family: var(--font-typewriter);
  text-align: center;
  padding: 2rem;
  background: var(--scrap-newsprint);
  box-shadow: var(--shadow-paper);
}

.progress-detail {
  color: var(--ink-grey);
  margin-top: 0.5rem;
}

/* ==========================================================================
   SUBMISSION LAYOUT
   ========================================================================== */

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
    min-width: 280px;
    max-width: 320px;
    position: sticky;
    top: 1rem;
    align-self: flex-start;
  }

  .tiles-section {
    flex: 2;
  }
}

.submission-controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.instruction {
  font-family: var(--font-typewriter);
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.05em;
  margin-bottom: 0;
}

.instruction-hint {
  font-family: var(--font-typewriter);
  font-size: 0.75rem;
  color: var(--ink-grey);
  margin-top: 0.25rem;
}

/* ==========================================================================
   MULTI-ROW ANSWER BOX
   ========================================================================== */

.answer-box {
  background: var(--scrap-white);
  padding: 0.75rem;
  min-height: 180px;
  border: 3px dashed var(--ink-charcoal);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;
}

.answer-box.has-content {
  border-style: solid;
}

.answer-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  min-height: 32px;
  padding: 0.4rem;
  background: rgba(0, 0, 0, 0.03);
  border: 2px dashed transparent;
  transition: all 0.2s;
  align-items: center;
}

.answer-row.empty {
  justify-content: center;
  background: rgba(0, 0, 0, 0.02);
}

.answer-row.drop-target {
  background: var(--scrap-cream);
  border-color: var(--accent-red);
}

.answer-row:not(.empty):hover {
  background: rgba(0, 0, 0, 0.05);
}

.row-placeholder {
  opacity: 0.3;
  font-size: 0.75rem;
  font-family: var(--font-typewriter);
}

.answer-tile {
  cursor: grab;
}

.answer-tile:active {
  cursor: grabbing;
}

.clear-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-danger);
  color: white;
  border: none;
  font-size: 0.7rem;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.clear-btn:hover {
  opacity: 1;
}

.placeholder {
  color: var(--ink-grey);
  font-style: italic;
  font-family: var(--font-typewriter);
  text-align: center;
}

/* Dragging state for tiles */
.tile.dragging {
  opacity: 0.5;
}

/* ==========================================================================
   TILES GRID - The heart of the game
   ========================================================================== */

.tiles-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 1rem;
  background: var(--color-background-mute);
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.1);
  justify-content: center;
}

@media (min-width: 640px) {
  .tiles-grid {
    gap: 0.5rem;
    padding: 1.25rem;
    justify-content: flex-start;
  }
}

@media (min-width: 1024px) {
  .tiles-grid {
    gap: 0.6rem;
    padding: 1.5rem;
  }
}

/* Tile styles are in main.css - just add scoped overrides if needed */

.submit-btn {
  width: 100%;
  padding: 1rem;
  background: var(--accent-red);
  color: white;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
}

.submit-btn:hover:not(:disabled) {
  background: var(--accent-red-dark);
  transform: rotate(0.5deg) scale(1.02);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ==========================================================================
   JUDGING AREA
   ========================================================================== */

.judging-area {
  text-align: center;
}

.submissions-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}

@media (min-width: 640px) {
  .submissions-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
}

.submission-card {
  padding: 1.25rem;
  background: var(--scrap-cream);
  border: none;
  font-size: 1rem;
  cursor: pointer;
  font-family: var(--font-typewriter);
  font-weight: 700;
  color: var(--ink-black);
  text-transform: lowercase;
  box-shadow: var(--shadow-paper);
  transition: transform 0.15s, box-shadow 0.15s;
}

.submission-card:hover:not(.readonly) {
  transform: scale(1.02) rotate(-0.5deg);
  box-shadow: var(--shadow-paper-hover);
}

.submission-card.readonly {
  cursor: default;
}

.submission-card.vote-option {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.submission-author {
  font-size: 0.8rem;
  color: var(--ink-grey);
  font-weight: 400;
}

/* ==========================================================================
   RESULTS AREA
   ========================================================================== */

.results-area {
  text-align: center;
}

.results-area h2 {
  font-family: var(--font-headline-2);
  font-size: clamp(1.5rem, 4vw, 2rem);
  margin-bottom: 1rem;
}

.results-area h2.you-win {
  color: var(--color-success);
  font-size: clamp(1.75rem, 5vw, 2.5rem);
}

.winner-card {
  background: var(--scrap-yellow);
  padding: 1.5rem;
  margin: 1rem auto;
  max-width: 500px;
  position: relative;
  box-shadow: var(--shadow-paper);
  transform: rotate(-1deg);
}

.winner-card.is-you {
  background: var(--scrap-green);
}

@media (min-width: 640px) {
  .winner-card {
    padding: 2rem;
  }
}

.winner-card .tape-strip {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%) rotate(3deg);
  width: 60px;
  height: 20px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 200, 0.85) 0%,
    rgba(255, 255, 180, 0.7) 100%
  );
  box-shadow: inset 0 0 4px rgba(255, 255, 255, 0.5), 0 2px 4px rgba(0, 0, 0, 0.1);
}

.winner-card.self-pick {
  background: var(--scrap-orange);
}

.winner-card.was-overruled {
  background: var(--scrap-green);
}

.winner-name {
  font-family: var(--font-headline-2);
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  color: var(--ink-black);
}

.winner-answer {
  font-family: var(--font-typewriter);
  font-size: 1.1rem;
  font-weight: 700;
  text-transform: lowercase;
  color: var(--ink-black);
}

.overrule-note {
  font-family: var(--font-typewriter);
  font-size: 0.8rem;
  color: var(--ink-grey);
  margin-top: 0.5rem;
  font-style: italic;
}

/* ==========================================================================
   ALL SUBMISSIONS
   ========================================================================== */

.all-submissions {
  margin: 2rem 0;
}

.all-submissions h3 {
  font-family: var(--font-headline-2);
  margin-bottom: 1rem;
  font-size: 1rem;
}

.submission-result {
  padding: 0.75rem 1rem;
  background: var(--scrap-newsprint);
  margin-bottom: 0.5rem;
  text-align: left;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
}

.submission-result .answer {
  font-family: var(--font-typewriter);
  font-weight: 700;
  text-transform: lowercase;
  color: var(--ink-black);
}

.submission-result.winner {
  background: var(--scrap-yellow);
  border-left: 4px solid var(--accent-yellow);
}

.submission-result.judge-self-pick {
  border-left: 4px solid var(--color-warning);
}

.player-name {
  font-family: var(--font-typewriter);
  font-weight: 700;
  color: var(--ink-black);
}

.judge-badge {
  font-family: var(--font-typewriter);
  font-size: 0.65rem;
  background: var(--accent-yellow);
  color: var(--ink-black);
  padding: 0.15rem 0.4rem;
  text-transform: uppercase;
}

/* ==========================================================================
   VOTING AREA
   ========================================================================== */

.voting-area {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--scrap-white);
  box-shadow: var(--shadow-paper);
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.vote-prompt {
  font-family: var(--font-typewriter);
  font-weight: 700;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
}

.vote-note {
  font-family: var(--font-typewriter);
  font-size: 0.8rem;
  color: var(--ink-grey);
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
    justify-content: center;
    gap: 1rem;
  }
}

.vote-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
}

.vote-btn.overrule {
  background: var(--color-danger);
  color: white;
}

.vote-btn.overrule:hover:not(:disabled) {
  background: var(--color-danger-hover);
  transform: rotate(-1deg) scale(1.02);
}

.vote-btn.keep {
  background: var(--color-success);
  color: white;
}

.vote-btn.keep:hover:not(:disabled) {
  background: var(--color-success-hover);
  transform: rotate(1deg) scale(1.02);
}

.vote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Vote Progress */
.vote-progress {
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--scrap-newsprint);
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.vote-progress-title {
  font-family: var(--font-typewriter);
  font-weight: 700;
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.vote-progress-bar {
  height: 20px;
  background: var(--scrap-white);
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
  background: var(--color-danger);
  left: 0;
}

.vote-progress-fill.against {
  background: var(--color-success);
}

.vote-progress-labels {
  font-family: var(--font-typewriter);
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.for-label { color: var(--color-danger); }
.against-label { color: var(--color-success); }
.pending-label { color: var(--ink-grey); }

.prompt-reminder {
  font-family: var(--font-typewriter);
  background: var(--scrap-cream);
  padding: 1rem;
  margin: 1rem auto;
  max-width: 500px;
  font-style: italic;
}

/* ==========================================================================
   GAME OVER
   ========================================================================== */

.game-over {
  text-align: center;
  padding: 2rem;
}

.game-over h1 {
  font-family: var(--font-display-2);
  font-size: clamp(2.5rem, 8vw, 4rem);
  margin-bottom: 2rem;
}

.you-win-final {
  color: var(--color-success);
}

.you-lose-final {
  color: var(--accent-red);
}

.final-scores {
  margin-bottom: 2rem;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.final-score {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--scrap-newsprint);
  margin-bottom: 0.5rem;
  font-family: var(--font-typewriter);
  box-shadow: var(--shadow-paper);
  animation: paperDrop 0.4s var(--animation-smooth) backwards;
}

.final-score.winner {
  background: var(--scrap-yellow);
  transform: rotate(-1deg);
}

.final-score.is-you {
  border-left: 4px solid var(--accent-red);
}

.game-over-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
}

@media (min-width: 480px) {
  .game-over-actions {
    flex-direction: row;
    justify-content: center;
  }
}

.play-again-btn {
  padding: 1rem 2rem;
  background: var(--color-success);
  color: white;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
}

.play-again-btn:hover {
  background: var(--color-success-hover);
  transform: rotate(0.5deg) scale(1.02);
}

.final-score .name {
  font-weight: 700;
}

.final-score .rank {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--accent-red);
}

/* ==========================================================================
   ACTION BUTTONS
   ========================================================================== */

.advance-btn {
  padding: 1rem 2rem;
  background: var(--accent-red);
  color: white;
  border: none;
  font-size: 1.1rem;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
}

.advance-btn:hover:not(:disabled) {
  background: var(--accent-red-dark);
  transform: rotate(0.5deg) scale(1.02);
}

.advance-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.waiting-text {
  font-family: var(--font-typewriter);
  color: var(--ink-grey);
  font-style: italic;
}

.leave-btn {
  padding: 1rem 2rem;
  background: var(--ink-black);
  color: var(--scrap-white);
  border: none;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: var(--shadow-paper);
}

.leave-btn:hover {
  background: var(--ink-charcoal);
}

.leave-game-btn {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  padding: 0.5rem 1rem;
  background: var(--color-danger);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 0.8rem;
  box-shadow: var(--shadow-paper);
  z-index: 100;
}

.leave-game-btn:hover {
  background: var(--color-danger-hover);
}

@media (max-width: 640px) {
  .game {
    padding-bottom: 70px;
  }

  .leave-game-btn {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 1rem;
    font-size: 0.9rem;
  }
}

/* ==========================================================================
   DISPLAY TILES - Used for showing submissions
   ========================================================================== */

.display-tile {
  cursor: default !important;
  pointer-events: none;
}

.display-tile.small {
  padding: 0.25rem 0.4rem;
  font-size: 0.85rem;
}

.submission-with-tiles {
  padding: 1rem;
}

.submission-tiles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  justify-content: center;
}

.winner-answer-tiles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  justify-content: center;
  margin-top: 0.5rem;
}

.answer-tiles-inline {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-left: 0.5rem;
}

/* ==========================================================================
   TILE STYLE VARIATIONS - Applied via class based on content hash
   ========================================================================== */

.tile-style-1 {
  font-family: var(--font-headline-1);
  background-color: var(--scrap-cream);
  transform: rotate(-2deg);
}

.tile-style-2 {
  font-family: var(--font-headline-2);
  background-color: var(--scrap-yellow);
  transform: rotate(1.5deg);
}

.tile-style-3 {
  font-family: var(--font-body-2);
  background-color: var(--scrap-newsprint);
  transform: rotate(-1deg);
}

.tile-style-4 {
  font-family: var(--font-headline-3);
  background-color: var(--scrap-pink);
  transform: rotate(2deg);
  font-style: italic;
}

.tile-style-5 {
  font-family: var(--font-headline-4);
  background-color: var(--scrap-blue);
  transform: rotate(-1.5deg);
}

.tile-style-6 {
  font-family: var(--font-headline-4);
  background-color: var(--scrap-white);
  transform: rotate(0.5deg);
}

.tile-style-7 {
  font-family: var(--font-display-1);
  background-color: var(--scrap-orange);
  transform: rotate(-2.5deg);
}

.tile-style-8 {
  font-family: var(--font-headline-1);
  background-color: var(--scrap-green);
  transform: rotate(1deg);
}

.tile-style-9 {
  font-family: var(--font-headline-2);
  background-color: var(--scrap-cream);
  transform: rotate(-1.5deg);
}

.tile-style-10 {
  font-family: var(--font-display-2);
  background-color: var(--scrap-pink);
  transform: rotate(2.5deg);
}

.tile-style-11 {
  font-family: var(--font-headline-3);
  background-color: var(--scrap-yellow);
  transform: rotate(-0.5deg);
  color: var(--accent-red);
}

.tile-style-12 {
  font-family: var(--font-body-2);
  background-color: var(--scrap-blue);
  transform: rotate(1.5deg);
}

.tile-style-13 {
  font-family: var(--font-blackletter);
  background-color: var(--scrap-cream);
  transform: rotate(-2deg);
}

.tile-style-14 {
  font-family: var(--font-headline-6);
  background-color: var(--scrap-newsprint);
  transform: rotate(0.5deg);
}

/* ==========================================================================
   ANIMATIONS
   ========================================================================== */

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

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-3px); }
  20%, 40%, 60%, 80% { transform: translateX(3px); }
}
</style>
