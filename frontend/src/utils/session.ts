const SESSION_KEY = 'ransom-notes-session'

export interface GameSession {
  gameId: string
  playerId: string
  nickname: string
  inviteCode: string
}

export function saveSession(session: GameSession): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function loadSession(): GameSession | null {
  const json = sessionStorage.getItem(SESSION_KEY)
  return json ? JSON.parse(json) : null
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY)
}
