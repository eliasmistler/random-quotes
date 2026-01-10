import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { PlayerInfo, GamePhase } from '@/types/game'
import * as api from '@/api/game'

export const useGameStore = defineStore('game', () => {
  const gameId = ref<string | null>(null)
  const playerId = ref<string | null>(null)
  const inviteCode = ref<string | null>(null)
  const phase = ref<GamePhase | null>(null)
  const players = ref<PlayerInfo[]>([])
  const myTiles = ref<string[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isInGame = computed(() => gameId.value !== null)
  const currentPlayer = computed(() => players.value.find((p) => p.id === playerId.value))
  const isHost = computed(() => currentPlayer.value?.is_host ?? false)
  const playerCount = computed(() => players.value.length)

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
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    }
  }

  function leaveGame() {
    gameId.value = null
    playerId.value = null
    inviteCode.value = null
    phase.value = null
    players.value = []
    myTiles.value = []
    error.value = null
  }

  return {
    gameId,
    playerId,
    inviteCode,
    phase,
    players,
    myTiles,
    isLoading,
    error,
    isInGame,
    currentPlayer,
    isHost,
    playerCount,
    createGame,
    joinGame,
    refreshGameState,
    leaveGame,
  }
})
