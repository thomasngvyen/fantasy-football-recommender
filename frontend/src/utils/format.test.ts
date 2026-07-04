import { describe, expect, it } from 'vitest'
import { breakdownRowsForPosition } from './format'

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
