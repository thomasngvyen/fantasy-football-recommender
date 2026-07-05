import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { PlayerOut, Position, WeekScheduleOut } from '../api/types'
import { POSITIONS } from '../api/types'
import { filterPlayers, formatPlayerLabel } from '../utils/format'

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

type PlayerPickerProps = {
  label: string
  players: PlayerOut[]
  selectedId: string
  excludeId: string
  filter: string
  disabled: boolean
  onChange: (id: string) => void
}

function PlayerPicker({
  label,
  players,
  selectedId,
  excludeId,
  filter,
  disabled,
  onChange,
}: PlayerPickerProps) {
  const selected = players.find((player) => player.sleeper_id === selectedId)
  const options = useMemo(
    () => filterPlayers(players, filter, excludeId),
    [players, filter, excludeId],
  )

  if (selected) {
    return (
      <div className="field__chosen">
        <span className="field__chosen-name">{formatPlayerLabel(selected)}</span>
        <button
          type="button"
          className="field__change"
          onClick={() => onChange('')}
          disabled={disabled}
        >
          Change
        </button>
      </div>
    )
  }

  return (
    <select
      className="field__control"
      value=""
      onChange={(e) => {
        if (e.target.value) {
          onChange(e.target.value)
        }
      }}
      disabled={disabled || options.length === 0}
    >
      <option value="" disabled>
        {options.length === 0 ? 'No matches — adjust search' : `Choose ${label}`}
      </option>
      {options.map((player) => (
        <option key={player.sleeper_id} value={player.sleeper_id}>
          {formatPlayerLabel(player)}
        </option>
      ))}
    </select>
  )
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

  const filteredCount = useMemo(
    () =>
      filterPlayers(players, playerFilter, '').filter(
        (player) =>
          player.sleeper_id !== playerAId && player.sleeper_id !== playerBId,
      ).length,
    [players, playerFilter, playerAId, playerBId],
  )

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
        {playerFilter.trim() ? (
          <span className="field__hint">
            {filteredCount} player{filteredCount === 1 ? '' : 's'} match
          </span>
        ) : null}
      </label>

      <div className="form-grid form-grid--players">
        <label className="field">
          <span className="field__label">Player A</span>
          <PlayerPicker
            label="player A"
            players={players}
            selectedId={playerAId}
            excludeId={playerBId}
            filter={playerFilter}
            disabled={loadingPlayers}
            onChange={onPlayerAChange}
          />
        </label>

        <label className="field">
          <span className="field__label">Player B</span>
          <PlayerPicker
            label="player B"
            players={players}
            selectedId={playerBId}
            excludeId={playerAId}
            filter={playerFilter}
            disabled={loadingPlayers}
            onChange={onPlayerBChange}
          />
        </label>
      </div>

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

      {!loadingPlayers &&
      players.length > 0 &&
      playerFilter.trim() &&
      filteredCount === 0 &&
      !playerAId &&
      !playerBId ? (
        <p className="form-status form-status--empty" role="status">
          No players match &ldquo;{playerFilter}&rdquo;.
        </p>
      ) : null}

      <button type="submit" className="btn-primary" disabled={!canCompare}>
        <span className="btn-primary__shine" aria-hidden />
        {comparing ? 'Comparing…' : 'Compare players'}
      </button>
    </form>
  )
}
