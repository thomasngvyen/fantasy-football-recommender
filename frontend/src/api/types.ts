export interface ProjectionBreakdown {
  base_projection: number
  home_advantage_modifier: number
  defense_rank_modifier: number
  total_offense_rank_modifier: number
  weather_modifier: number
  final_projection: number
  weather_notes?: string | null
}

export interface ComparePlayerResult {
  sleeper_id: string
  name: string
  position: string
  team: string | null
  opponent: string | null
  adjusted_points: number
  breakdown: ProjectionBreakdown
  explanation: string
}

export interface CompareRequest {
  player_a_id: string
  player_b_id: string
  week: number
  season: number
}

export interface CompareResponse {
  week: number
  season: number
  winner: ComparePlayerResult
  loser: ComparePlayerResult
  margin_of_victory: number
  recommendation: string
}

export interface PlayerOut {
  sleeper_id: string
  name: string
  position: string
  team: string | null
}

export const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DST'] as const
export type Position = (typeof POSITIONS)[number]
