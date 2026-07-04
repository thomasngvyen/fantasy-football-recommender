import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { PlayerOut, Position, WeekScheduleOut } from '../api/types'
import { POSITIONS } from '../api/types'
import { formatPlayerLabel } from '../utils/format'

type CompareFormProps = {
  position: Position
  week: number
  season: number
  weekInfo: WeekScheduleOut | null
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
  weekInfo,
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
  const [playerFilter, setPlayerFilter] = useState('')

  const filteredPlayers = useMemo(() => {
    const query = playerFilter.trim().toLowerCase()
    if (!query) return players
    return players.filter((player) =>
      formatPlayerLabel(player).toLowerCase().includes(query),
    )
  }, [playerFilter, players])

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
          {weekInfo && weekInfo.teams_on_bye.length > 0 ? (
            <span className="field__hint">
              Bye week: {weekInfo.teams_on_bye.join(', ')}
            </span>
          ) : weekInfo ? (
            <span className="field__hint">Full slate ({weekInfo.game_count} games)</span>
          ) : null}
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

      <label className="field">
        <span className="field__label">Search players</span>
        <input
          className="field__control"
          type="search"
          placeholder="Filter by name or team…"
          value={playerFilter}
          onChange={(e) => setPlayerFilter(e.target.value)}
          disabled={loadingPlayers || players.length === 0}
        />
      </label>

      {loadingPlayers ? (
        <p className="form-status form-status--loading" aria-live="polite">
          Loading players from Sleeper…
        </p>
      ) : null}

      {!loadingPlayers && players.length === 0 ? (
        <p className="form-status form-status--empty" role="status">
          No rosterable {position} players found. Try another position or check the API
          connection.
        </p>
      ) : null}

      {!loadingPlayers && players.length > 0 && filteredPlayers.length === 0 ? (
        <p className="form-status form-status--empty" role="status">
          No players match &ldquo;{playerFilter}&rdquo;.
        </p>
      ) : null}

      <div className="form-grid form-grid--players">
        <label className="field">
          <span className="field__label">Player A</span>
          <select
            className="field__control"
            value={playerAId}
            onChange={(e) => onPlayerAChange(e.target.value)}
            disabled={loadingPlayers || filteredPlayers.length === 0}
          >
            {filteredPlayers.map((player) => (
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
            disabled={loadingPlayers || filteredPlayers.length === 0}
          >
            {filteredPlayers.map((player) => (
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
