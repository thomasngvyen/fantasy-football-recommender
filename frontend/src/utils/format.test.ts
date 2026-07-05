import { describe, expect, it } from 'vitest'
import { breakdownRowsForPosition, filterPlayers } from './format'

const PLAYERS = [
  { sleeper_id: '1', name: 'Patrick Mahomes', position: 'QB', team: 'KC' },
  { sleeper_id: '2', name: 'Josh Allen', position: 'QB', team: 'BUF' },
  { sleeper_id: '3', name: 'Lamar Jackson', position: 'QB', team: 'BAL' },
]

describe('breakdownRowsForPosition', () => {
  it('hides matchup row for DST', () => {
    const keys = breakdownRowsForPosition('DST').map((row) => row.key)
    expect(keys).not.toContain('defense_rank_modifier')
    expect(keys).toContain('total_offense_rank_modifier')
  })

  it('hides opp offense row for skill positions', () => {
    const keys = breakdownRowsForPosition('QB').map((row) => row.key)
    expect(keys).toContain('defense_rank_modifier')
    expect(keys).not.toContain('total_offense_rank_modifier')
  })
})

describe('filterPlayers', () => {
  it('filters by name or team without changing order', () => {
    const matches = filterPlayers(PLAYERS, 'allen')
    expect(matches.map((player) => player.sleeper_id)).toEqual(['2'])
  })

  it('excludes a player id from results', () => {
    const matches = filterPlayers(PLAYERS, '', '1')
    expect(matches.map((player) => player.sleeper_id)).toEqual(['2', '3'])
  })

  it('returns all players when filter is empty', () => {
    expect(filterPlayers(PLAYERS, '')).toHaveLength(3)
  })
})
