import type { CompareResponse, PlayerOut } from '../api/types'

export const BREAKDOWN_ROWS: {
  key: Exclude<keyof CompareResponse['winner']['breakdown'], 'weather_notes'>
  label: string
}[] = [
  { key: 'base_projection', label: 'Base' },
  { key: 'home_advantage_modifier', label: 'Home' },
  { key: 'defense_rank_modifier', label: 'Matchup' },
  { key: 'total_offense_rank_modifier', label: 'Opp offense' },
  { key: 'weather_modifier', label: 'Weather' },
  { key: 'final_projection', label: 'Final' },
]

export function formatBreakdownValue(
  key: Exclude<keyof CompareResponse['winner']['breakdown'], 'weather_notes'>,
  value: number,
): string {
  if (key === 'base_projection' || key === 'final_projection') {
    return value.toFixed(2)
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`
}

export function breakdownRowsForPosition(position: string) {
  return BREAKDOWN_ROWS.filter(({ key }) => {
    if (key === 'defense_rank_modifier') {
      return position !== 'DST'
    }
    if (key === 'total_offense_rank_modifier') {
      return position === 'DST'
    }
    return true
  })
}

export function formatPlayerLabel(player: PlayerOut): string {
  const team = player.team ? ` (${player.team})` : ''
  return `${player.name}${team}`
}

export function filterPlayers(
  players: PlayerOut[],
  filter: string,
  excludeId = '',
): PlayerOut[] {
  const query = filter.trim().toLowerCase()
  return players.filter((player) => {
    if (excludeId && player.sleeper_id === excludeId) {
      return false
    }
    if (!query) {
      return true
    }
    return formatPlayerLabel(player).toLowerCase().includes(query)
  })
}
