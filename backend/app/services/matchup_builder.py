import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import Matchup, Player

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
STADIUMS_PATH = FIXTURES_DIR / "stadiums.json"


def schedule_path_for_week(week: int) -> Path:
    return FIXTURES_DIR / f"week{week}_schedule.json"


def build_matchups(session: Session, week: int, season: int) -> dict:
    """
    Load the week schedule fixture and upsert Matchup rows for all players
    on each team. Caller is responsible for session.commit().
    """
    schedule_path = schedule_path_for_week(week)

    if not schedule_path.exists() or not STADIUMS_PATH.exists():
        return {
            "status": "error",
            "message": f"Missing fixture(s): {schedule_path.name} or stadiums.json",
        }

    stadiums_data = json.loads(STADIUMS_PATH.read_text(encoding="utf-8"))
    dome_lookup = {item["team"]: item["is_dome"] for item in stadiums_data}
    games_list = json.loads(schedule_path.read_text(encoding="utf-8"))

    matchups_created = 0
    matchups_updated = 0

    for game in games_list:
        team_id = game["team"]
        opponent_id = game["opponent"]
        is_home_game = game["is_home"]

        dt_str = game["game_datetime"].replace("Z", "+00:00")
        kickoff_time = datetime.fromisoformat(dt_str)

        host_team = team_id if is_home_game else opponent_id
        is_game_in_dome = dome_lookup.get(host_team, False)

        roster_players = session.scalars(
            select(Player).where(Player.team == team_id)
        ).all()

        for player in roster_players:
            existing_matchup = session.execute(
                select(Matchup).where(
                    Matchup.player_id == player.id,
                    Matchup.week == week,
                    Matchup.season == season,
                )
            ).scalar_one_or_none()

            if existing_matchup:
                existing_matchup.opponent = opponent_id
                existing_matchup.is_home = is_home_game
                existing_matchup.is_dome = is_game_in_dome
                existing_matchup.game_datetime = kickoff_time
                matchups_updated += 1
            else:
                session.add(
                    Matchup(
                        player_id=player.id,
                        week=week,
                        season=season,
                        opponent=opponent_id,
                        is_home=is_home_game,
                        is_dome=is_game_in_dome,
                        game_datetime=kickoff_time,
                    )
                )
                matchups_created += 1

    return {
        "status": "success",
        "week": week,
        "season": season,
        "schedule_file": schedule_path.name,
        "matchups_created": matchups_created,
        "matchups_updated": matchups_updated,
    }


def build_week1_matchups(session: Session) -> dict:
    """Backward-compatible helper for the Week 1 / 2026 dev fixture."""
    return build_matchups(session, week=1, season=2026)
