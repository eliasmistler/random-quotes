import type { GameCreatedResponse, GameJoinedResponse, GameStateResponse } from '@/types/game'

const API_BASE = 'http://localhost:8000/api'

export async function createGame(hostNickname: string): Promise<GameCreatedResponse> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ host_nickname: hostNickname }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to create game')
  }

  return response.json()
}

export async function joinGame(inviteCode: string, nickname: string): Promise<GameJoinedResponse> {
  const response = await fetch(`${API_BASE}/games/join/${inviteCode}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ nickname }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to join game')
  }

  return response.json()
}

export async function getGameState(gameId: string, playerId: string): Promise<GameStateResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}?player_id=${playerId}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to get game state')
  }

  return response.json()
}
