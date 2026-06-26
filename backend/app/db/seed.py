from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.db.tables import Player, TeamMatchupStats
from app.services.base_projections import fetch_season_averages, resolve_base_projection
from app.services.sleeper_client import SleeperClient

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFENSE_RANKS_PATH = FIXTURES_DIR / "defense_ranks.json"


def seed_team_matchup_stats(session: Session) -> int:
    rows = json.loads(DEFENSE_RANKS_PATH.read_text())
    count = 0

    for row in rows:
        existing = session.execute(
            select(TeamMatchupStats).where(
                TeamMatchupStats.team == row["team"],
                TeamMatchupStats.season == row["season"],
            )
        ).scalar_one_or_none()

        if existing is None:
            session.add(TeamMatchupStats(**row))
        else:
            existing.pass_defense_rank = row["pass_defense_rank"]
            existing.run_defense_rank = row["run_defense_rank"]
            existing.total_offense_rank = row["total_offense_rank"]
            existing.points_allowed_pass_avg = row.get("points_allowed_pass_avg")
            existing.points_allowed_run_avg = row.get("points_allowed_run_avg")

        count += 1

    return count


def seed_players(
    session: Session,
    client: SleeperClient,
    *,
    player_ids: list[str] | None = None,
    refresh: bool = False,
    stats_season: int | None = 2025,
    scoring: str = "half_ppr",
    prune_inactive: bool = True,
) -> int:
    if player_ids:
        records = [
            record
            for player_id in player_ids
            if (record := client.get_player_record(player_id, refresh=refresh))
        ]
    else:
        records = client.get_player_records(refresh=refresh)

    active_sleeper_ids = {row["sleeper_id"] for row in records}
    if prune_inactive and not player_ids:
        prune_players_not_on_roster(session, active_sleeper_ids)

    season_averages = (
        fetch_season_averages(stats_season, scoring=scoring)
        if stats_season is not None
        else None
    )

    players_by_id = client.get_all_players(refresh=refresh)

    count = 0
    for row in records:
        sleeper_player = players_by_id.get(row["sleeper_id"])
        row["base_projection"] = resolve_base_projection(
            sleeper_id=row["sleeper_id"],
            position=row["position"],
            season_averages=season_averages,
            sleeper_player=sleeper_player,
        )

        existing = session.execute(
            select(Player).where(Player.sleeper_id == row["sleeper_id"])
        ).scalar_one_or_none()

        if existing is None:
            session.add(Player(**row))
        else:
            existing.name = row["name"]
            existing.position = row["position"]
            existing.team = row["team"]
            existing.base_projection = row["base_projection"]

        count += 1

    return count


def prune_players_not_on_roster(session: Session, active_sleeper_ids: set[str]) -> int:
    """Remove DB players who are no longer on an NFL roster per Sleeper."""
    removed = 0
    for player in session.scalars(select(Player)).all():
        if player.sleeper_id not in active_sleeper_ids:
            session.delete(player)
            removed += 1
    return removed


def run_seed(
    *,
    stats: bool = True,
    players: bool = True,
    player_ids: list[str] | None = None,
    refresh_players: bool = False,
    stats_season: int | None = 2025,
    scoring: str = "half_ppr",
) -> None:
    init_db()
    client = SleeperClient()

    with SessionLocal() as session:
        if stats:
            stats_count = seed_team_matchup_stats(session)
            print(f"Seeded {stats_count} team matchup stat rows")

        if players:
            if stats_season is not None:
                print(f"Loading {stats_season} per-game averages ({scoring})...")
            players_count = seed_players(
                session,
                client,
                player_ids=player_ids,
                refresh=refresh_players,
                stats_season=stats_season,
                scoring=scoring,
            )
            print(f"Seeded {players_count} players")

        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the fantasy football database")
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only load defense_ranks.json into team_matchup_stats",
    )
    parser.add_argument(
        "--players-only",
        action="store_true",
        help="Only load players from Sleeper",
    )
    parser.add_argument(
        "--player-id",
        action="append",
        dest="player_ids",
        help="Seed specific Sleeper player IDs (can be repeated)",
    )
    parser.add_argument(
        "--refresh-players",
        action="store_true",
        help="Bypass Sleeper player cache and fetch fresh data",
    )
    parser.add_argument(
        "--stats-season",
        type=int,
        default=2025,
        help="Season for per-player base_projection averages (default: 2025)",
    )
    parser.add_argument(
        "--no-season-averages",
        action="store_true",
        help="Use position defaults instead of last-season averages",
    )
    parser.add_argument(
        "--scoring",
        choices=["half_ppr", "ppr", "std"],
        default="half_ppr",
        help="Fantasy scoring format for season averages",
    )
    args = parser.parse_args()

    seed_stats = not args.players_only
    seed_player_rows = not args.stats_only

    if args.stats_only and args.players_only:
        parser.error("Use only one of --stats-only or --players-only")

    run_seed(
        stats=seed_stats,
        players=seed_player_rows,
        player_ids=args.player_ids,
        refresh_players=args.refresh_players,
        stats_season=None if args.no_season_averages else args.stats_season,
        scoring=args.scoring,
    )


if __name__ == "__main__":
    main()
