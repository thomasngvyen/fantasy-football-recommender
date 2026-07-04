import type { CompareResponse } from '../api/types'
import { PlayerCard } from './PlayerCard'

type ResultsSectionProps = {
  result: CompareResponse
}

export function ResultsSection({ result }: ResultsSectionProps) {
  return (
    <section className="results animate-in animate-in--3">
      <div className="recommendation panel panel--accent">
        <p className="recommendation__eyebrow">Recommendation</p>
        <h2 className="recommendation__title">{result.recommendation}</h2>
        <p className="recommendation__meta">
          Week {result.week}, {result.season} · Margin{' '}
          <strong>{result.margin_of_victory.toFixed(2)} pts</strong>
        </p>
      </div>

      <div className="player-grid">
        <PlayerCard
          label="Start"
          player={result.winner}
          highlight
          delayClass="animate-in--4"
        />
        <PlayerCard label="Sit" player={result.loser} delayClass="animate-in--5" />
      </div>
    </section>
  )
}
