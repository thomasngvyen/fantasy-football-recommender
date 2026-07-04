import { StatusPill } from './StatusPill'

type HeroHeaderProps = {
  apiOnline: boolean | null
}

export function HeroHeader({ apiOnline }: HeroHeaderProps) {
  return (
    <header className="hero animate-in animate-in--1">
      <div className="hero__glow" aria-hidden />
      <div className="hero__content">
        <p className="hero__eyebrow">Fantasy Football Recommender</p>
        <h1 className="hero__title">
          Who do I <span className="hero__accent">start?</span>
        </h1>
        <p className="hero__subtitle">
          Compare adjusted weekly projections powered by matchup data, home-field
          advantage, and weather — all in one clean decision.
        </p>
      </div>
      <StatusPill online={apiOnline} />
    </header>
  )
}
