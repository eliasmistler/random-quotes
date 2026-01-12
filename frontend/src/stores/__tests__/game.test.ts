import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGameStore } from '../game'
import * as api from '@/api/game'

vi.mock('@/api/game')

const mockApi = vi.mocked(api)

describe('useGameStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('has correct initial values', () => {
      const store = useGameStore()

      expect(store.gameId).toBeNull()
      expect(store.playerId).toBeNull()
      expect(store.inviteCode).toBeNull()
      expect(store.phase).toBeNull()
      expect(store.players).toEqual([])
      expect(store.myTiles).toEqual([])
      expect(store.currentRound).toBeNull()
      expect(store.config).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('isInGame returns false when not in game', () => {
      const store = useGameStore()
      expect(store.isInGame).toBe(false)
    })

    it('isInGame returns true when in game', () => {
      const store = useGameStore()
      store.gameId = 'test-game-id'
      expect(store.isInGame).toBe(true)
    })

    it('currentPlayer returns the player matching playerId', () => {
      const store = useGameStore()
      store.playerId = 'player-1'
      store.players = [
        { id: 'player-1', nickname: 'Alice', score: 0, is_host: true, is_connected: true },
        { id: 'player-2', nickname: 'Bob', score: 1, is_host: false, is_connected: true },
      ]

      expect(store.currentPlayer?.nickname).toBe('Alice')
    })

    it('isHost returns true when current player is host', () => {
      const store = useGameStore()
      store.playerId = 'player-1'
      store.players = [
        { id: 'player-1', nickname: 'Alice', score: 0, is_host: true, is_connected: true },
      ]

      expect(store.isHost).toBe(true)
    })

    it('isHost returns false when current player is not host', () => {
      const store = useGameStore()
      store.playerId = 'player-2'
      store.players = [
        { id: 'player-1', nickname: 'Alice', score: 0, is_host: true, is_connected: true },
        { id: 'player-2', nickname: 'Bob', score: 0, is_host: false, is_connected: true },
      ]

      expect(store.isHost).toBe(false)
    })

    it('playerCount returns number of players', () => {
      const store = useGameStore()
      store.players = [
        { id: 'player-1', nickname: 'Alice', score: 0, is_host: true, is_connected: true },
        { id: 'player-2', nickname: 'Bob', score: 0, is_host: false, is_connected: true },
        { id: 'player-3', nickname: 'Charlie', score: 0, is_host: false, is_connected: true },
      ]

      expect(store.playerCount).toBe(3)
    })

    it('isJudge returns true when current player is judge', () => {
      const store = useGameStore()
      store.currentRound = {
        round_number: 1,
        prompt: { id: 'prompt-1', text: 'Test prompt' },
        judge_id: 'player-1',
        submissions: [],
        winner_id: null,
        has_submitted: false,
        is_judge: true,
      }

      expect(store.isJudge).toBe(true)
    })

    it('hasSubmitted returns true when player has submitted', () => {
      const store = useGameStore()
      store.currentRound = {
        round_number: 1,
        prompt: { id: 'prompt-1', text: 'Test prompt' },
        judge_id: 'player-1',
        submissions: [],
        winner_id: null,
        has_submitted: true,
        is_judge: false,
      }

      expect(store.hasSubmitted).toBe(true)
    })

    it('judge returns the judge player', () => {
      const store = useGameStore()
      store.players = [
        { id: 'player-1', nickname: 'Alice', score: 0, is_host: true, is_connected: true },
        { id: 'player-2', nickname: 'Bob', score: 0, is_host: false, is_connected: true },
      ]
      store.currentRound = {
        round_number: 1,
        prompt: { id: 'prompt-1', text: 'Test prompt' },
        judge_id: 'player-2',
        submissions: [],
        winner_id: null,
        has_submitted: false,
        is_judge: false,
      }

      expect(store.judge?.nickname).toBe('Bob')
    })

    it('roundWinner returns the winner player', () => {
      const store = useGameStore()
      store.players = [
        { id: 'player-1', nickname: 'Alice', score: 1, is_host: true, is_connected: true },
        { id: 'player-2', nickname: 'Bob', score: 0, is_host: false, is_connected: true },
      ]
      store.currentRound = {
        round_number: 1,
        prompt: { id: 'prompt-1', text: 'Test prompt' },
        judge_id: 'player-2',
        submissions: [],
        winner_id: 'player-1',
        has_submitted: false,
        is_judge: false,
      }

      expect(store.roundWinner?.nickname).toBe('Alice')
    })
  })

  describe('createGame', () => {
    it('creates game and sets state', async () => {
      const store = useGameStore()
      const mockResponse = {
        game_id: 'game-123',
        invite_code: 'ABC123',
        player_id: 'player-1',
        player: {
          id: 'player-1',
          nickname: 'TestHost',
          score: 0,
          is_host: true,
          is_connected: true,
          word_tiles: ['word1', 'word2'],
        },
      }
      const mockGameState = {
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'lobby' as const,
        players: [
          { id: 'player-1', nickname: 'TestHost', score: 0, is_host: true, is_connected: true },
        ],
        current_round: null,
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: ['word1', 'word2'],
      }

      mockApi.createGame.mockResolvedValue(mockResponse)
      mockApi.getGameState.mockResolvedValue(mockGameState)

      await store.createGame('TestHost')

      expect(mockApi.createGame).toHaveBeenCalledWith('TestHost')
      expect(store.gameId).toBe('game-123')
      expect(store.playerId).toBe('player-1')
      expect(store.inviteCode).toBe('ABC123')
      expect(store.phase).toBe('lobby')
    })

    it('sets error on failure', async () => {
      const store = useGameStore()
      mockApi.createGame.mockRejectedValue(new Error('Network error'))

      await expect(store.createGame('TestHost')).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
    })

    it('sets loading state during request', async () => {
      const store = useGameStore()
      let loadingDuringRequest = false

      mockApi.createGame.mockImplementation(async () => {
        loadingDuringRequest = store.isLoading
        return {
          game_id: 'game-123',
          invite_code: 'ABC123',
          player_id: 'player-1',
          player: {
            id: 'player-1',
            nickname: 'TestHost',
            score: 0,
            is_host: true,
            is_connected: true,
            word_tiles: [],
          },
        }
      })
      mockApi.getGameState.mockResolvedValue({
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'lobby',
        players: [],
        current_round: null,
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: [],
      })

      await store.createGame('TestHost')

      expect(loadingDuringRequest).toBe(true)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('joinGame', () => {
    it('joins game and sets state', async () => {
      const store = useGameStore()
      const mockResponse = {
        game_id: 'game-123',
        player_id: 'player-2',
        player: {
          id: 'player-2',
          nickname: 'Player2',
          score: 0,
          is_host: false,
          is_connected: true,
          word_tiles: [],
        },
      }
      const mockGameState = {
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'lobby' as const,
        players: [
          { id: 'player-1', nickname: 'Host', score: 0, is_host: true, is_connected: true },
          { id: 'player-2', nickname: 'Player2', score: 0, is_host: false, is_connected: true },
        ],
        current_round: null,
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: [],
      }

      mockApi.joinGame.mockResolvedValue(mockResponse)
      mockApi.getGameState.mockResolvedValue(mockGameState)

      await store.joinGame('abc123', 'Player2')

      expect(mockApi.joinGame).toHaveBeenCalledWith('abc123', 'Player2')
      expect(store.gameId).toBe('game-123')
      expect(store.playerId).toBe('player-2')
      expect(store.inviteCode).toBe('ABC123')
    })

    it('sets error on failure', async () => {
      const store = useGameStore()
      mockApi.joinGame.mockRejectedValue(new Error('Game not found'))

      await expect(store.joinGame('INVALID', 'Player')).rejects.toThrow('Game not found')
      expect(store.error).toBe('Game not found')
    })
  })

  describe('startGame', () => {
    it('starts game and refreshes state', async () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-1'

      mockApi.startGame.mockResolvedValue({ success: true, message: 'Game started' })
      mockApi.getGameState.mockResolvedValue({
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'round_submission',
        players: [],
        current_round: {
          round_number: 1,
          prompt: { id: 'prompt-1', text: 'Test' },
          judge_id: 'player-1',
          submissions: [],
          winner_id: null,
          has_submitted: false,
          is_judge: true,
        },
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: ['tile1', 'tile2'],
      })

      await store.startGame()

      expect(mockApi.startGame).toHaveBeenCalledWith('game-123', 'player-1')
      expect(store.phase).toBe('round_submission')
    })

    it('does nothing if not in game', async () => {
      const store = useGameStore()

      await store.startGame()

      expect(mockApi.startGame).not.toHaveBeenCalled()
    })
  })

  describe('submitResponse', () => {
    it('submits response and refreshes state', async () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-2'

      mockApi.submitResponse.mockResolvedValue({ success: true, message: 'Submitted' })
      mockApi.getGameState.mockResolvedValue({
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'round_submission',
        players: [],
        current_round: {
          round_number: 1,
          prompt: { id: 'prompt-1', text: 'Test' },
          judge_id: 'player-1',
          submissions: [],
          winner_id: null,
          has_submitted: true,
          is_judge: false,
        },
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: ['tile3', 'tile4'],
      })

      await store.submitResponse(['tile1', 'tile2'])

      expect(mockApi.submitResponse).toHaveBeenCalledWith('game-123', 'player-2', ['tile1', 'tile2'])
    })
  })

  describe('selectWinner', () => {
    it('selects winner and refreshes state', async () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-1'

      mockApi.selectWinner.mockResolvedValue({ success: true, message: 'Winner selected' })
      mockApi.getGameState.mockResolvedValue({
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'round_results',
        players: [],
        current_round: {
          round_number: 1,
          prompt: { id: 'prompt-1', text: 'Test' },
          judge_id: 'player-1',
          submissions: [],
          winner_id: 'player-2',
          has_submitted: false,
          is_judge: true,
        },
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: [],
      })

      await store.selectWinner('player-2')

      expect(mockApi.selectWinner).toHaveBeenCalledWith('game-123', 'player-1', 'player-2')
      expect(store.phase).toBe('round_results')
    })
  })

  describe('advanceRound', () => {
    it('advances round and refreshes state', async () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-1'

      mockApi.advanceRound.mockResolvedValue({ success: true, message: 'Next round' })
      mockApi.getGameState.mockResolvedValue({
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'round_submission',
        players: [],
        current_round: {
          round_number: 2,
          prompt: { id: 'prompt-2', text: 'Test 2' },
          judge_id: 'player-2',
          submissions: [],
          winner_id: null,
          has_submitted: false,
          is_judge: false,
        },
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: [],
      })

      await store.advanceRound()

      expect(mockApi.advanceRound).toHaveBeenCalledWith('game-123', 'player-1')
      expect(store.currentRound?.round_number).toBe(2)
    })
  })

  describe('leaveGame', () => {
    it('resets all state', () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-1'
      store.inviteCode = 'ABC123'
      store.phase = 'lobby'
      store.players = [
        { id: 'player-1', nickname: 'Test', score: 0, is_host: true, is_connected: true },
      ]
      store.myTiles = ['tile1', 'tile2']
      store.error = 'some error'

      store.leaveGame()

      expect(store.gameId).toBeNull()
      expect(store.playerId).toBeNull()
      expect(store.inviteCode).toBeNull()
      expect(store.phase).toBeNull()
      expect(store.players).toEqual([])
      expect(store.myTiles).toEqual([])
      expect(store.currentRound).toBeNull()
      expect(store.config).toBeNull()
      expect(store.error).toBeNull()
    })
  })

  describe('refreshGameState', () => {
    it('updates state from API', async () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-1'

      mockApi.getGameState.mockResolvedValue({
        game_id: 'game-123',
        invite_code: 'ABC123',
        phase: 'round_submission',
        players: [
          { id: 'player-1', nickname: 'Alice', score: 2, is_host: true, is_connected: true },
          { id: 'player-2', nickname: 'Bob', score: 1, is_host: false, is_connected: true },
        ],
        current_round: {
          round_number: 3,
          prompt: { id: 'prompt-3', text: 'Test prompt' },
          judge_id: 'player-1',
          submissions: [],
          winner_id: null,
          has_submitted: false,
          is_judge: true,
        },
        config: {
          tiles_per_player: 7,
          points_to_win: 3,
          submission_time_seconds: 60,
          judging_time_seconds: 30,
          min_players: 2,
          max_players: 8,
        },
        my_tiles: ['word1', 'word2', 'word3'],
      })

      await store.refreshGameState()

      expect(store.phase).toBe('round_submission')
      expect(store.players.length).toBe(2)
      expect(store.myTiles).toEqual(['word1', 'word2', 'word3'])
      expect(store.currentRound?.round_number).toBe(3)
    })

    it('does nothing if not in game', async () => {
      const store = useGameStore()

      await store.refreshGameState()

      expect(mockApi.getGameState).not.toHaveBeenCalled()
    })

    it('sets error on failure', async () => {
      const store = useGameStore()
      store.gameId = 'game-123'
      store.playerId = 'player-1'

      mockApi.getGameState.mockRejectedValue(new Error('Failed to fetch'))

      await store.refreshGameState()

      expect(store.error).toBe('Failed to fetch')
    })
  })
})
