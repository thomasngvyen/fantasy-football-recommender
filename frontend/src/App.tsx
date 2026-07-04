import { useCallback, useEffect, useState } from 'react'
import { checkHealth, comparePlayers, getPlayers, getScheduleWeek } from './api/client'
import type { CompareResponse, Position, WeekScheduleOut } from './api/types'
import { CompareForm } from './components/CompareForm'
import { HeroHeader } from './components/HeroHeader'
import { ResultsSection } from './components/ResultsSection'
import './App.css'

function App() {
  const [position, setPosition] = useState<Position>('QB')
  const [week, setWeek] = useState(1)
  const [season, setSeason] = useState(2026)
  const [weekInfo, setWeekInfo] = useState<WeekScheduleOut | null>(null)
  const [players, setPlayers] = useState<Awaited<ReturnType<typeof getPlayers>>>([])
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

  useEffect(() => {
    void getScheduleWeek(week)
      .then(setWeekInfo)
      .catch(() => setWeekInfo(null))
  }, [week])

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
    Boolean(playerAId && playerBId && playerAId !== playerBId) &&
    !comparing &&
    !loadingPlayers

  return (
    <div className="app">
      <HeroHeader apiOnline={apiOnline} />

      <CompareForm
        position={position}
        week={week}
        season={season}
        weekInfo={weekInfo}
        players={players}
        playerAId={playerAId}
        playerBId={playerBId}
        loadingPlayers={loadingPlayers}
        comparing={comparing}
        canCompare={canCompare}
        onPositionChange={setPosition}
        onWeekChange={setWeek}
        onSeasonChange={setSeason}
        onPlayerAChange={setPlayerAId}
        onPlayerBChange={setPlayerBId}
        onSubmit={handleCompare}
      />

      {error ? (
        <p className="banner banner--error animate-in animate-in--3" role="alert">
          {error}
        </p>
      ) : null}

      {apiOnline === false ? (
        <p className="banner banner--error animate-in animate-in--3" role="alert">
          Start the backend with{' '}
          <code>python -m uvicorn app.main:app --reload</code> from the backend folder.
        </p>
      ) : null}

      {comparing ? (
        <section className="panel loading-panel animate-in animate-in--3" aria-live="polite">
          <p className="loading-panel__text">Running projection compare…</p>
        </section>
      ) : null}

      {result && !comparing ? <ResultsSection result={result} /> : null}
    </div>
  )
}

export default App
