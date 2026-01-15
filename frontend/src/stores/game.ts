import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { PlayerInfo, GamePhase, RoundInfo, GameConfig, ChatMessage } from '@/types/game'
import * as api from '@/api/game'
import { GameWebSocket } from '@/services/websocket'

export const useGameStore = defineStore('game', () => {
  const ws = new GameWebSocket()
  const gameId = ref<string | null>(null)
  const playerId = ref<string | null>(null)
  const inviteCode = ref<string | null>(null)
  const phase = ref<GamePhase | null>(null)
  const players = ref<PlayerInfo[]>([])
  const myTiles = ref<string[]>([])
  const currentRound = ref<RoundInfo | null>(null)
  const config = ref<GameConfig | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const chatMessages = ref<ChatMessage[]>([])
  const unreadChatCount = ref(0)

  const isInGame = computed(() => gameId.value !== null)
  const currentPlayer = computed(() => players.value.find((p) => p.id === playerId.value))
  const isHost = computed(() => currentPlayer.value?.is_host ?? false)
  const playerCount = computed(() => players.value.length)
  const isJudge = computed(() => currentRound.value?.is_judge ?? false)
  const hasSubmitted = computed(() => currentRound.value?.has_submitted ?? false)
  const judge = computed(() => {
    if (!currentRound.value) return null
    return players.value.find((p) => p.id === currentRound.value?.judge_id) ?? null
  })
  const roundWinner = computed(() => {
    if (!currentRound.value?.winner_id) return null
    return players.value.find((p) => p.id === currentRound.value?.winner_id) ?? null
  })

  // Overrule voting computed properties
  const judgePickedSelf = computed(() => currentRound.value?.judge_picked_self ?? false)
  const canOverruleVote = computed(() => currentRound.value?.can_overrule_vote ?? false)
  const hasCastOverruleVote = computed(() => currentRound.value?.has_cast_overrule_vote ?? false)
  const isOverruled = computed(() => currentRound.value?.overruled ?? false)
  const canWinnerVote = computed(() => currentRound.value?.can_winner_vote ?? false)
  const hasCastWinnerVote = computed(() => currentRound.value?.has_cast_winner_vote ?? false)
  const overruleVoteCount = computed(() => Object.keys(currentRound.value?.overrule_votes ?? {}).length)
  const winnerVoteCount = computed(() => Object.keys(currentRound.value?.winner_votes ?? {}).length)
  function connectWebSocket() {
    if (!gameId.value || !playerId.value) return

    ws.onMessage(async (data) => {
      const message = data as { type: string; data?: ChatMessage }
      if (message.type === 'game_update') {
        await refreshGameState()
      } else if (message.type === 'chat_message' && message.data) {
        chatMessages.value.push(message.data)
        unreadChatCount.value++
      }
    })

    ws.connect(gameId.value, playerId.value)
  }

  async function createGame(nickname: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.createGame(nickname)
      gameId.value = response.game_id
      playerId.value = response.player_id
      inviteCode.value = response.invite_code
      phase.value = 'lobby'
      players.value = [
        {
          id: response.player.id,
          nickname: response.player.nickname,
          score: response.player.score,
          is_host: response.player.is_host,
          is_connected: response.player.is_connected,
        },
      ]
      myTiles.value = response.player.word_tiles
      chatMessages.value = []
      unreadChatCount.value = 0
      // Fetch full game state to populate config
      await refreshGameState()
      connectWebSocket()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function joinGame(code: string, nickname: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.joinGame(code, nickname)
      gameId.value = response.game_id
      playerId.value = response.player_id
      inviteCode.value = code.toUpperCase()
      await refreshGameState()
      await loadChatHistory()
      connectWebSocket()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function refreshGameState() {
    if (!gameId.value || !playerId.value) return

    try {
      const state = await api.getGameState(gameId.value, playerId.value)
      phase.value = state.phase
      players.value = state.players
      myTiles.value = state.my_tiles
      inviteCode.value = state.invite_code
      currentRound.value = state.current_round
      config.value = state.config
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    }
  }

  async function startGame() {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.startGame(gameId.value, playerId.value)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function submitResponse(tilesUsed: string[]) {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.submitResponse(gameId.value, playerId.value, tilesUsed)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function selectWinner(winnerPlayerId: string) {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.selectWinner(gameId.value, playerId.value, winnerPlayerId)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function advanceRound() {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.advanceRound(gameId.value, playerId.value)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function castOverruleVote(voteToOverrule: boolean) {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.castOverruleVote(gameId.value, playerId.value, voteToOverrule)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function castWinnerVote(winnerPlayerId: string) {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.castWinnerVote(gameId.value, playerId.value, winnerPlayerId)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function loadChatHistory() {
    if (!gameId.value || !playerId.value) return

    try {
      const response = await api.getChatHistory(gameId.value, playerId.value)
      chatMessages.value = response.messages
      unreadChatCount.value = 0
    } catch (e) {
      console.error('Failed to load chat history:', e)
    }
  }

  async function sendChatMessage(text: string) {
    if (!gameId.value || !playerId.value) return

    try {
      await api.sendChatMessage(gameId.value, playerId.value, text)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    }
  }

  function markChatAsRead() {
    unreadChatCount.value = 0
  }

  async function restartGame() {
    if (!gameId.value || !playerId.value) return

    isLoading.value = true
    error.value = null

    try {
      await api.restartGame(gameId.value, playerId.value)
      await refreshGameState()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function leaveGame() {
    ws.disconnect()
    gameId.value = null
    playerId.value = null
    inviteCode.value = null
    phase.value = null
    players.value = []
    myTiles.value = []
    currentRound.value = null
    config.value = null
    error.value = null
    chatMessages.value = []
    unreadChatCount.value = 0
  }

  return {
    gameId,
    playerId,
    inviteCode,
    phase,
    players,
    myTiles,
    currentRound,
    config,
    isLoading,
    error,
    chatMessages,
    unreadChatCount,
    isInGame,
    currentPlayer,
    isHost,
    playerCount,
    isJudge,
    hasSubmitted,
    judge,
    roundWinner,
    judgePickedSelf,
    canOverruleVote,
    hasCastOverruleVote,
    isOverruled,
    canWinnerVote,
    hasCastWinnerVote,
    overruleVoteCount,
    winnerVoteCount,
    createGame,
    joinGame,
    refreshGameState,
    startGame,
    submitResponse,
    selectWinner,
    advanceRound,
    castOverruleVote,
    castWinnerVote,
    restartGame,
    leaveGame,
    loadChatHistory,
    sendChatMessage,
    markChatAsRead,
  }
})
