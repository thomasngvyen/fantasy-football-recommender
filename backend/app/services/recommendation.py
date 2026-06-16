from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal, init_db
from app.db.tables import Matchup, Player, Projection, TeamMatchupStats
from app.services.projection import compute_adjusted_projection
from app.services.sleeper_client import SleeperClient

NEUTRAL_RANK = 16


@dataclass(frozen=True)
class RecommendationResult:
    player_id: int
    player_name: str
    position: str
    team: str | None
    opponent: str
    adjusted_points: float
    breakdown: dict


def effective_base_projection(player: Player) -> float:
    return player.base_projection


def _get_opponent_stats(
    session: Session, opponent: str, season: int
) -> TeamMatchupStats | None:
    return session.execute(
        select(TeamMatchupStats).where(
            TeamMatchupStats.team == opponent,
            TeamMatchupStats.season == season,
        )
    ).scalar_one_or_none()


def recommend_for_matchup(
    session: Session, player: Player, matchup: Matchup
) -> tuple[float, dict]:
    stats = _get_opponent_stats(session, matchup.opponent, matchup.season)
    pass_rank = stats.pass_defense_rank if stats else NEUTRAL_RANK
    run_rank = stats.run_defense_rank if stats else NEUTRAL_RANK
    offense_rank = stats.total_offense_rank if stats else NEUTRAL_RANK

    weather = matchup.weather
    wind_mph = weather.wind_mph if weather else 0.0
    is_rain = weather.is_rain if weather else False

    base = effective_base_projection(player)
    return compute_adjusted_projection(
        base=base,
        position=player.position,
        is_home=matchup.is_home,
        defense_rank_passing=pass_rank,
        defense_rank_run=run_rank,
        total_offense_rank=offense_rank,
        wind_mph=wind_mph,
        is_dome=matchup.is_dome,
        rain=is_rain,
    )


def upsert_projection(
    session: Session,
    player: Player,
    matchup: Matchup,
    adjusted_points: float,
    breakdown: dict,
) -> Projection:
    existing = session.execute(
        select(Projection).where(Projection.matchup_id == matchup.id)
    ).scalar_one_or_none()

    if existing is None:
        projection = Projection(
            player_id=player.id,
            matchup_id=matchup.id,
            week=matchup.week,
            season=matchup.season,
            adjusted_points=adjusted_points,
            breakdown_json=breakdown,
        )
        session.add(projection)
        return projection

    existing.adjusted_points = adjusted_points
    existing.breakdown_json = breakdown
    existing.week = matchup.week
    existing.season = matchup.season
    return existing


def compute_projections_for_week(
    session: Session, week: int, season: int
) -> dict:
    matchups = session.scalars(
        select(Matchup)
        .where(Matchup.week == week, Matchup.season == season)
        .options(selectinload(Matchup.player), selectinload(Matchup.weather))
    ).all()

    created = 0
    updated = 0
    skipped = 0
    results: list[RecommendationResult] = []

    for matchup in matchups:
        player = matchup.player
        if player is None:
            skipped += 1
            continue

        adjusted_points, breakdown = recommend_for_matchup(session, player, matchup)
        existing = session.execute(
            select(Projection).where(Projection.matchup_id == matchup.id)
        ).scalar_one_or_none()

        upsert_projection(session, player, matchup, adjusted_points, breakdown)

        if existing is None:
            created += 1
        else:
            updated += 1

        results.append(
            RecommendationResult(
                player_id=player.id,
                player_name=player.name,
                position=player.position,
                team=player.team,
                opponent=matchup.opponent,
                adjusted_points=adjusted_points,
                breakdown=breakdown,
            )
        )

    return {
        "status": "success",
        "week": week,
        "season": season,
        "projections_created": created,
        "projections_updated": updated,
        "skipped": skipped,
        "results": results,
    }


def resolve_week_season(
    client: SleeperClient,
    *,
    week: int | None,
    season: int | None,
) -> tuple[int, int]:
    state = client.get_nfl_state()
    resolved_season = season if season is not None else state.season
    resolved_week = week if week is not None else (state.display_week or state.week)

    if resolved_week == 0:
        resolved_week = 1

    return resolved_week, resolved_season


def run_recommendations(
    *,
    week: int | None = None,
    season: int | None = None,
    limit: int | None = None,
) -> None:
    init_db()
    client = SleeperClient()
    target_week, target_season = resolve_week_season(
        client, week=week, season=season
    )

    with SessionLocal() as session:
        summary = compute_projections_for_week(session, target_week, target_season)
        session.commit()

    print(
        f"Projections for season {summary['season']} week {summary['week']}: "
        f"{summary['projections_created']} created, "
        f"{summary['projections_updated']} updated, "
        f"{summary['skipped']} skipped"
    )

    top = sorted(
        summary["results"],
        key=lambda row: row.adjusted_points,
        reverse=True,
    )
    if limit is not None:
        top = top[:limit]

    for row in top:
        print(
            f"  {row.player_name} ({row.position}, {row.team}) vs {row.opponent}: "
            f"{row.adjusted_points:.2f} pts"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute and store adjusted projections for a week"
    )
    parser.add_argument("--week", type=int, help="NFL week (default: from Sleeper)")
    parser.add_argument("--season", type=int, help="NFL season (default: from Sleeper)")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Print top N projections after run (default: 10, use 0 for none)",
    )
    args = parser.parse_args()

    run_recommendations(
        week=args.week,
        season=args.season,
        limit=None if args.limit == 0 else args.limit,
    )


if __name__ == "__main__":
    main()
