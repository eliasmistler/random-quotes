/**
 * WebSocket service for real-time game updates.
 */

type MessageHandler = (data: unknown) => void

export class GameWebSocket {
  private ws: WebSocket | null = null
  private messageHandler: MessageHandler | null = null
  private gameId: string | null = null
  private playerId: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  connect(gameId: string, playerId: string): void {
    this.gameId = gameId
    this.playerId = playerId
    this.reconnectAttempts = 0
    this.doConnect()
  }

  private doConnect(): void {
    if (!this.gameId || !this.playerId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = 'localhost:8000'
    const url = `${protocol}//${host}/api/ws/game/${this.gameId}?player_id=${this.playerId}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (this.messageHandler) {
          this.messageHandler(data)
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      this.ws = null

      // Attempt reconnection if not intentionally closed
      if (event.code !== 1000 && this.gameId && this.playerId) {
        this.attemptReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    console.log(`Attempting reconnection in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      if (this.gameId && this.playerId) {
        this.doConnect()
      }
    }, delay)
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandler = handler
  }

  disconnect(): void {
    this.gameId = null
    this.playerId = null
    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting')
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}
