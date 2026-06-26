"""
Weekly sync: NFL state from Sleeper → seed DB → build matchups.

Run from the backend directory:
    python scripts/sync_week.py
    python scripts/sync_week.py --week 1 --season 2026
    python scripts/sync_week.py --matchups-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.config  # noqa: F401, E402  # loads backend/.env before other app imports

from app.db.seed import seed_players, seed_team_matchup_stats  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services.matchup_builder import build_matchups, schedule_path_for_week  # noqa: E402
from app.services.recommendation import compute_projections_for_week  # noqa: E402
from app.services.sleeper_client import SleeperClient  # noqa: E402
from app.services.weather_client import WeatherClient, sync_weather_for_week  # noqa: E402


def resolve_week_season(
    client: SleeperClient,
    *,
    week: int | None,
    season: int | None,
) -> tuple[int, int]:
    state = client.get_nfl_state()

    resolved_season = season if season is not None else state.season
    resolved_week = week

    if resolved_week is None:
        resolved_week = state.display_week or state.week

    if resolved_week == 0:
        resolved_week = 1
        print(
            "Note: NFL is in offseason (week 0). Defaulting to week 1. "
            "Pass --week explicitly to override."
        )

    return resolved_week, resolved_season


def resolve_stats_season(
    client: SleeperClient,
    stats_season: int | None,
) -> int | None:
    if stats_season is not None:
        return stats_season
    state = client.get_nfl_state()
    return int(state.previous_season)


def run_sync(
    *,
    week: int | None = None,
    season: int | None = None,
    stats: bool = True,
    players: bool = True,
    matchups: bool = True,
    weather: bool = True,
    projections: bool = True,
    refresh_players: bool = True,
    stats_season: int | None = None,
    scoring: str = "half_ppr",
    use_season_averages: bool = True,
) -> None:
    init_db()
    client = SleeperClient()
    target_week, target_season = resolve_week_season(
        client, week=week, season=season
    )
    average_season = (
        resolve_stats_season(client, stats_season)
        if use_season_averages
        else None
    )

    print(f"Sync target: season {target_season}, week {target_week}")
    if average_season is not None:
        print(f"Base projections from {average_season} averages ({scoring})")

    if matchups and not schedule_path_for_week(target_week).exists():
        print(
            f"Error: no schedule fixture at fixtures/week{target_week}_schedule.json"
        )
        sys.exit(1)

    with SessionLocal() as session:
        if stats:
            count = seed_team_matchup_stats(session)
            print(f"Upserted {count} team matchup stat rows")

        if players:
            count = seed_players(
                session,
                client,
                refresh=refresh_players,
                stats_season=average_season,
                scoring=scoring,
            )
            print(f"Upserted {count} players from Sleeper")

        if matchups:
            result = build_matchups(session, target_week, target_season)
            if result["status"] == "error":
                session.rollback()
                print(f"Error: {result['message']}")
                sys.exit(1)
            print(
                f"Matchups from {result['schedule_file']}: "
                f"{result['matchups_created']} created, "
                f"{result['matchups_updated']} updated"
            )

        if weather:
            weather_client = WeatherClient.from_env()
            if weather_client is None:
                print(
                    "Weather: skipped (set OPENWEATHER_API_KEY in backend/.env)"
                )
            else:
                weather_result = sync_weather_for_week(
                    session, target_week, target_season, weather_client
                )
                print(
                    f"Weather: {weather_result['games_fetched']} games fetched, "
                    f"{weather_result['rows_created']} created, "
                    f"{weather_result['rows_updated']} updated, "
                    f"{weather_result['forecast_unavailable']} outside forecast window, "
                    f"{weather_result['skipped_dome']} dome skipped"
                )
                for error in weather_result["errors"]:
                    print(f"  Weather error: {error}")

        if projections:
            projection_result = compute_projections_for_week(
                session, target_week, target_season
            )
            print(
                f"Projections: {projection_result['projections_created']} created, "
                f"{projection_result['projections_updated']} updated"
            )

        session.commit()
        print("Sync complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync players and matchups for the current NFL week"
    )
    parser.add_argument(
        "--week",
        type=int,
        help="NFL week (default: from Sleeper get_nfl_state())",
    )
    parser.add_argument(
        "--season",
        type=int,
        help="NFL season year (default: from Sleeper get_nfl_state())",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only upsert team stats from defense_ranks.json",
    )
    parser.add_argument(
        "--players-only",
        action="store_true",
        help="Only upsert players from Sleeper",
    )
    parser.add_argument(
        "--matchups-only",
        action="store_true",
        help="Only upsert matchups (requires schedule fixture for target week)",
    )
    parser.add_argument(
        "--weather-only",
        action="store_true",
        help="Only fetch/cache weather for outdoor matchups",
    )
    parser.add_argument(
        "--no-weather",
        action="store_true",
        help="Skip weather fetch during full sync",
    )
    parser.add_argument(
        "--projections-only",
        action="store_true",
        help="Only compute/store adjusted projections",
    )
    parser.add_argument(
        "--no-projections",
        action="store_true",
        help="Skip projection step during full sync",
    )
    parser.add_argument(
        "--no-refresh-players",
        action="store_true",
        help="Reuse cached Sleeper player payload instead of re-downloading",
    )
    parser.add_argument(
        "--stats-season",
        type=int,
        help="Season for per-player base averages (default: Sleeper previous_season)",
    )
    parser.add_argument(
        "--no-season-averages",
        action="store_true",
        help="Use position defaults instead of last-season averages for base_projection",
    )
    parser.add_argument(
        "--scoring",
        choices=["half_ppr", "ppr", "std"],
        default="half_ppr",
        help="Fantasy scoring format for season averages",
    )
    args = parser.parse_args()

    exclusive = sum(
        [
            args.stats_only,
            args.players_only,
            args.matchups_only,
            args.weather_only,
            args.projections_only,
        ]
    )
    if exclusive > 1:
        parser.error(
            "Use at most one of --stats-only, --players-only, "
            "--matchups-only, --weather-only, --projections-only"
        )

    run_sync(
        week=args.week,
        season=args.season,
        stats=not args.players_only
        and not args.matchups_only
        and not args.weather_only
        and not args.projections_only,
        players=not args.stats_only
        and not args.matchups_only
        and not args.weather_only
        and not args.projections_only,
        matchups=not args.stats_only
        and not args.players_only
        and not args.weather_only
        and not args.projections_only,
        weather=not args.no_weather
        and not args.stats_only
        and not args.players_only
        and not args.matchups_only
        and not args.projections_only,
        projections=not args.no_projections
        and not args.stats_only
        and not args.players_only
        and not args.matchups_only
        and not args.weather_only,
        refresh_players=not args.no_refresh_players,
        stats_season=args.stats_season,
        scoring=args.scoring,
        use_season_averages=not args.no_season_averages,
    )


if __name__ == "__main__":
    main()
