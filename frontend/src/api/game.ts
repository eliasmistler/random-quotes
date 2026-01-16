import type {
  ActionResponse,
  ChatHistoryResponse,
  GameCreatedResponse,
  GameJoinedResponse,
  GameStateResponse,
} from '@/types/game'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

/**
 * Extract error message from API response.
 * Handles various error response formats and provides helpful debugging info.
 */
async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      const error = await response.json()
      const message = error.detail?.error || error.detail || error.message || fallback
      const code = error.detail?.code || ''
      console.error(`API Error [${response.status}${code ? ` ${code}` : ''}]:`, message)
      return message
    } else {
      const text = await response.text()
      console.error(`API Error [${response.status}]:`, text || fallback)
      return text || fallback
    }
  } catch {
    console.error(`API Error [${response.status}]: Could not parse error response`)
    return fallback
  }
}

export async function createGame(hostNickname: string): Promise<GameCreatedResponse> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ host_nickname: hostNickname }),
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to create game')
    throw new Error(message)
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
    const message = await extractErrorMessage(response, 'Failed to join game')
    throw new Error(message)
  }

  return response.json()
}

export async function getGameState(gameId: string, playerId: string): Promise<GameStateResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}?player_id=${playerId}`)

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to get game state')
    throw new Error(message)
  }

  return response.json()
}

export async function startGame(gameId: string, playerId: string): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/start?player_id=${playerId}`, {
    method: 'POST',
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to start game')
    throw new Error(message)
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
    const message = await extractErrorMessage(response, 'Failed to submit response')
    throw new Error(message)
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
    const message = await extractErrorMessage(response, 'Failed to select winner')
    throw new Error(message)
  }

  return response.json()
}

export async function advanceRound(gameId: string, playerId: string): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/advance?player_id=${playerId}`, {
    method: 'POST',
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to advance round')
    throw new Error(message)
  }

  return response.json()
}

export async function castOverruleVote(
  gameId: string,
  playerId: string,
  voteToOverrule: boolean,
): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/overrule?player_id=${playerId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ vote_to_overrule: voteToOverrule }),
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to cast overrule vote')
    throw new Error(message)
  }

  return response.json()
}

export async function castWinnerVote(
  gameId: string,
  playerId: string,
  winnerPlayerId: string,
): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/vote-winner?player_id=${playerId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ winner_player_id: winnerPlayerId }),
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to cast winner vote')
    throw new Error(message)
  }

  return response.json()
}

export async function restartGame(gameId: string, playerId: string): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/restart?player_id=${playerId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to restart game')
    throw new Error(message)
  }

  return response.json()
}

export async function addBot(gameId: string, playerId: string): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/add-bot?player_id=${playerId}`, {
    method: 'POST',
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to add bot')
    throw new Error(message)
  }

  return response.json()
}

export async function sendChatMessage(
  gameId: string,
  playerId: string,
  text: string,
): Promise<ActionResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/chat?player_id=${playerId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  })

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to send message')
    throw new Error(message)
  }

  return response.json()
}

export async function getChatHistory(
  gameId: string,
  playerId: string,
  limit: number = 100,
): Promise<ChatHistoryResponse> {
  const response = await fetch(
    `${API_BASE}/games/${gameId}/chat?player_id=${playerId}&limit=${limit}`,
  )

  if (!response.ok) {
    const message = await extractErrorMessage(response, 'Failed to get chat history')
    throw new Error(message)
  }

  return response.json()
}
