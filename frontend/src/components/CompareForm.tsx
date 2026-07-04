import type { FormEvent } from 'react'
import type { PlayerOut, Position } from '../api/types'
import { POSITIONS } from '../api/types'
import { formatPlayerLabel } from '../utils/format'

type CompareFormProps = {
  position: Position
  week: number
  season: number
  players: PlayerOut[]
  playerAId: string
  playerBId: string
  loadingPlayers: boolean
  comparing: boolean
  canCompare: boolean
  onPositionChange: (position: Position) => void
  onWeekChange: (week: number) => void
  onSeasonChange: (season: number) => void
  onPlayerAChange: (id: string) => void
  onPlayerBChange: (id: string) => void
  onSubmit: (event: FormEvent) => void
}

export function CompareForm({
  position,
  week,
  season,
  players,
  playerAId,
  playerBId,
  loadingPlayers,
  comparing,
  canCompare,
  onPositionChange,
  onWeekChange,
  onSeasonChange,
  onPlayerAChange,
  onPlayerBChange,
  onSubmit,
}: CompareFormProps) {
  return (
    <form className="compare-form panel animate-in animate-in--2" onSubmit={onSubmit}>
      <div className="form-grid">
        <label className="field">
          <span className="field__label">Position</span>
          <select
            className="field__control"
            value={position}
            onChange={(e) => onPositionChange(e.target.value as Position)}
          >
            {POSITIONS.map((pos) => (
              <option key={pos} value={pos}>
                {pos}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Week</span>
          <input
            className="field__control"
            type="number"
            min={1}
            max={18}
            value={week}
            onChange={(e) => onWeekChange(Number(e.target.value))}
          />
        </label>

        <label className="field">
          <span className="field__label">Season</span>
          <input
            className="field__control"
            type="number"
            min={2020}
            max={2035}
            value={season}
            onChange={(e) => onSeasonChange(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="form-grid form-grid--players">
        <label className="field">
          <span className="field__label">Player A</span>
          <select
            className="field__control"
            value={playerAId}
            onChange={(e) => onPlayerAChange(e.target.value)}
            disabled={loadingPlayers || players.length === 0}
          >
            {players.map((player) => (
              <option key={player.sleeper_id} value={player.sleeper_id}>
                {formatPlayerLabel(player)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Player B</span>
          <select
            className="field__control"
            value={playerBId}
            onChange={(e) => onPlayerBChange(e.target.value)}
            disabled={loadingPlayers || players.length === 0}
          >
            {players.map((player) => (
              <option key={player.sleeper_id} value={player.sleeper_id}>
                {formatPlayerLabel(player)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <button type="submit" className="btn-primary" disabled={!canCompare}>
        <span className="btn-primary__shine" aria-hidden />
        {comparing ? 'Comparing…' : 'Compare players'}
      </button>
    </form>
  )
}
