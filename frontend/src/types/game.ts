export type GamePhase =
  | 'lobby'
  | 'round_submission'
  | 'round_judging'
  | 'round_results'
  | 'game_over'

export interface Player {
  id: string
  nickname: string
  score: number
  is_host: boolean
  is_connected: boolean
  word_tiles: string[]
}

export interface PlayerInfo {
  id: string
  nickname: string
  score: number
  is_host: boolean
  is_connected: boolean
}

export interface GameConfig {
  tiles_per_player: number
  points_to_win: number
  submission_time_seconds: number
  judging_time_seconds: number
  min_players: number
  max_players: number
}

export interface Prompt {
  id: string
  text: string
}

export interface SubmissionInfo {
  player_id: string
  response_text: string
}

export interface RoundInfo {
  round_number: number
  prompt: Prompt
  judge_id: string
  submissions: SubmissionInfo[]
  winner_id: string | null
  has_submitted: boolean
  is_judge: boolean
}

export interface GameCreatedResponse {
  game_id: string
  invite_code: string
  player_id: string
  player: Player
}

export interface GameJoinedResponse {
  game_id: string
  player_id: string
  player: Player
}

export interface GameStateResponse {
  game_id: string
  invite_code: string
  phase: GamePhase
  players: PlayerInfo[]
  current_round: RoundInfo | null
  config: GameConfig
  my_tiles: string[]
}

export interface ActionResponse {
  success: boolean
  message: string
}
