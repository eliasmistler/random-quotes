import type {
  ActionResponse,
  GameCreatedResponse,
  GameJoinedResponse,
  GameStateResponse,
} from '@/types/game'

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

export async function startGame(gameId: string, playerId: string): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/start?player_id=${playerId}`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to start game')
  }

  return response.json()
}

export async function submitResponse(
  gameId: string,
  playerId: string,
  tilesUsed: string[],
): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/submit?player_id=${playerId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tiles_used: tilesUsed }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to submit response')
  }

  return response.json()
}

export async function selectWinner(
  gameId: string,
  playerId: string,
  winnerPlayerId: string,
): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/judge?player_id=${playerId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ winner_player_id: winnerPlayerId }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to select winner')
  }

  return response.json()
}

export async function advanceRound(gameId: string, playerId: string): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/advance?player_id=${playerId}`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.error || 'Failed to advance round')
  }

  return response.json()
}
