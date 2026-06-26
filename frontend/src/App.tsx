import { useCallback, useEffect, useState } from 'react'
import { checkHealth, comparePlayers, getPlayers } from './api/client'
import type { CompareResponse, PlayerOut, Position } from './api/types'
import { POSITIONS } from './api/types'
import './App.css'

const BREAKDOWN_ROWS: { key: Exclude<keyof CompareResponse['winner']['breakdown'], 'weather_notes'>; label: string }[] = [
  { key: 'base_projection', label: 'Base' },
  { key: 'home_advantage_modifier', label: 'Home' },
  { key: 'defense_rank_modifier', label: 'Matchup' },
  { key: 'total_offense_rank_modifier', label: 'Opp offense' },
  { key: 'weather_modifier', label: 'Weather' },
  { key: 'final_projection', label: 'Final' },
]

function formatBreakdownValue(
  key: Exclude<keyof CompareResponse['winner']['breakdown'], 'weather_notes'>,
  value: number,
): string {
  if (key === 'base_projection' || key === 'final_projection') {
    return value.toFixed(2)
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`
}

function formatPlayerLabel(player: PlayerOut): string {
  const team = player.team ? ` (${player.team})` : ''
  return `${player.name}${team}`
}

function PlayerCard({
  label,
  player,
  highlight,
}: {
  label: string
  player: CompareResponse['winner']
  highlight?: boolean
}) {
  return (
    <article className={`player-card${highlight ? ' player-card--winner' : ''}`}>
      <header>
        <span className="player-card__label">{label}</span>
        <h3>{player.name}</h3>
        <p className="player-card__meta">
          {player.position}
          {player.team ? ` · ${player.team}` : ''}
          {player.opponent ? ` vs ${player.opponent}` : ''}
        </p>
        <p className="player-card__score">{player.adjusted_points.toFixed(2)} pts</p>
      </header>
      <table className="breakdown-table">
        <tbody>
          {BREAKDOWN_ROWS.map(({ key, label: rowLabel }) => (
            <tr key={key}>
              <th>{rowLabel}</th>
              <td>{formatBreakdownValue(key, player.breakdown[key])}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {player.breakdown.weather_notes ? (
        <p className="player-card__note">{player.breakdown.weather_notes}</p>
      ) : null}
      <p className="player-card__explanation">{player.explanation}</p>
    </article>
  )
}

function App() {
  const [position, setPosition] = useState<Position>('QB')
  const [week, setWeek] = useState(1)
  const [season, setSeason] = useState(2026)
  const [players, setPlayers] = useState<PlayerOut[]>([])
  const [playerAId, setPlayerAId] = useState('')
  const [playerBId, setPlayerBId] = useState('')
  const [loadingPlayers, setLoadingPlayers] = useState(false)
  const [comparing, setComparing] = useState(false)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CompareResponse | null>(null)

  const loadPlayers = useCallback(async (pos: Position) => {
    setLoadingPlayers(true)
    setError(null)
    try {
      const data = await getPlayers(pos)
      setPlayers(data)
      setPlayerAId((current) =>
        data.some((p) => p.sleeper_id === current) ? current : (data[0]?.sleeper_id ?? ''),
      )
      setPlayerBId((current) => {
        if (data.some((p) => p.sleeper_id === current)) return current
        return data[1]?.sleeper_id ?? data[0]?.sleeper_id ?? ''
      })
    } catch (err) {
      setPlayers([])
      setPlayerAId('')
      setPlayerBId('')
      setError(err instanceof Error ? err.message : 'Failed to load players')
    } finally {
      setLoadingPlayers(false)
    }
  }, [])

  useEffect(() => {
    void checkHealth().then(setApiOnline)
  }, [])

  useEffect(() => {
    void loadPlayers(position)
  }, [position, loadPlayers])

  async function handleCompare(event: React.FormEvent) {
    event.preventDefault()
    if (!playerAId || !playerBId || playerAId === playerBId) return

    setComparing(true)
    setError(null)
    setResult(null)

    try {
      const response = await comparePlayers({
        player_a_id: playerAId,
        player_b_id: playerBId,
        week,
        season,
      })
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Compare failed')
    } finally {
      setComparing(false)
    }
  }

  const canCompare =
    playerAId && playerBId && playerAId !== playerBId && !comparing && !loadingPlayers

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <p className="eyebrow">Fantasy Football Recommender</p>
          <h1>Who do I start?</h1>
          <p className="subtitle">
            Compare adjusted weekly projections using matchup, home field, and weather.
          </p>
        </div>
        <div className={`status-pill${apiOnline ? ' status-pill--ok' : ''}`}>
          {apiOnline === null ? 'Checking API…' : apiOnline ? 'API online' : 'API offline'}
        </div>
      </header>

      <form className="compare-form" onSubmit={handleCompare}>
        <div className="form-grid">
          <label>
            Position
            <select
              value={position}
              onChange={(e) => setPosition(e.target.value as Position)}
            >
              {POSITIONS.map((pos) => (
                <option key={pos} value={pos}>
                  {pos}
                </option>
              ))}
            </select>
          </label>

          <label>
            Week
            <input
              type="number"
              min={1}
              max={18}
              value={week}
              onChange={(e) => setWeek(Number(e.target.value))}
            />
          </label>

          <label>
            Season
            <input
              type="number"
              min={2020}
              max={2035}
              value={season}
              onChange={(e) => setSeason(Number(e.target.value))}
            />
          </label>
        </div>

        <div className="form-grid form-grid--players">
          <label>
            Player A
            <select
              value={playerAId}
              onChange={(e) => setPlayerAId(e.target.value)}
              disabled={loadingPlayers || players.length === 0}
            >
              {players.map((player) => (
                <option key={player.sleeper_id} value={player.sleeper_id}>
                  {formatPlayerLabel(player)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Player B
            <select
              value={playerBId}
              onChange={(e) => setPlayerBId(e.target.value)}
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

        <button type="submit" className="compare-button" disabled={!canCompare}>
          {comparing ? 'Comparing…' : 'Compare players'}
        </button>
      </form>

      {error ? <p className="banner banner--error">{error}</p> : null}

      {apiOnline === false ? (
        <p className="banner banner--error">
          Start the backend with{' '}
          <code>python -m uvicorn app.main:app --reload</code> from the backend folder.
        </p>
      ) : null}

      {result ? (
        <section className="results">
          <div className="recommendation">
            <h2>Recommendation</h2>
            <p>{result.recommendation}</p>
            <p className="recommendation__meta">
              Week {result.week}, {result.season} · Margin {result.margin_of_victory.toFixed(2)} pts
            </p>
          </div>

          <div className="player-grid">
            <PlayerCard label="Start" player={result.winner} highlight />
            <PlayerCard label="Sit" player={result.loser} />
          </div>
        </section>
      ) : null}
    </div>
  )
}

export default App
