import type { CompareResponse } from '../api/types'
import { breakdownRowsForPosition, formatBreakdownValue } from '../utils/format'

type PlayerCardProps = {
  label: string
  player: CompareResponse['winner']
  highlight?: boolean
  delayClass?: string
}

export function PlayerCard({
  label,
  player,
  highlight,
  delayClass = '',
}: PlayerCardProps) {
  return (
    <article
      className={`player-card animate-in ${delayClass}${highlight ? ' player-card--winner' : ''}`}
    >
      <header className="player-card__header">
        <span className="player-card__label">{label}</span>
        <h3 className="player-card__name">{player.name}</h3>
        <p className="player-card__meta">
          {player.position}
          {player.team ? ` · ${player.team}` : ''}
          {player.opponent ? ` vs ${player.opponent}` : ''}
        </p>
        <p className="player-card__score">{player.adjusted_points.toFixed(2)} pts</p>
      </header>

      <table className="breakdown-table">
        <tbody>
          {breakdownRowsForPosition(player.position).map(({ key, label: rowLabel }) => (
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
