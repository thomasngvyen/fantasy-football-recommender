import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.tables import Matchup, Player

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SCHEDULE_PATH = FIXTURES_DIR / "week1_schedule.json"
STADIUMS_PATH = FIXTURES_DIR / "stadiums.json"


def build_week1_matchups(db: Session) -> dict:
    """
    Parses the Week 1 schedule fixture, resolves stadium weather environments,
    and bulk-generates/updates Matchup records for all assigned NFL players.
    """
    if not SCHEDULE_PATH.exists() or not STADIUMS_PATH.exists():
        return {"status": "error", "message": "Required JSON fixture files are missing."}

    # 1. Map stadium dome statuses into an optimized hash map
    with open(STADIUMS_PATH, encoding="utf-8") as f:
        stadiums_data = json.load(f)
    dome_lookup = {item["team"]: item["is_dome"] for item in stadiums_data}

    # 2. Extract schedule data array
    with open(SCHEDULE_PATH, encoding="utf-8") as f:
        games_list = json.load(f)

    matchups_created = 0
    matchups_updated = 0

    print("Executing Matchup Generation Engine for 2026 Week 1...")

    for game in games_list:
        team_id = game["team"]
        opponent_id = game["opponent"]
        is_home_game = game["is_home"]
        
        # Parse ISO format datetime string into a timezone-aware Python object
        dt_str = game["game_datetime"].replace("Z", "+00:00")
        kickoff_time = datetime.fromisoformat(dt_str)

        # Determine structural dome classification based on the location of the host venue
        host_team = team_id if is_home_game else opponent_id
        is_game_in_dome = dome_lookup.get(host_team, False)

        # 3. Pull all players whose active team string matches the current schedule row
        roster_players = db.query(Player).filter(Player.team == team_id).all()

        for player in roster_players:
            # Check if a matchup matrix row already exists via composite indexing keys
            existing_matchup = db.query(Matchup).filter(
                Matchup.player_id == player.id,
                Matchup.week == 1,
                Matchup.season == 2026
            ).first()

            if existing_matchup:
                # Update existing records to reflect any live rescheduling data
                existing_matchup.opponent = opponent_id
                existing_matchup.is_home = is_home_game
                existing_matchup.is_dome = is_game_in_dome
                existing_matchup.game_datetime = kickoff_time
                matchups_updated += 1
            else:
                # Construct a fresh Matchup entry mapped to the parent Player row
                new_matchup = Matchup(
                    player_id=player.id,
                    week=1,
                    season=2026,
                    opponent=opponent_id,
                    is_home=is_home_game,
                    is_dome=is_game_in_dome,
                    game_datetime=kickoff_time
                )
                db.add(new_matchup)
                matchups_created += 1

    db.commit()
    
    return {
        "status": "success",
        "matchups_created": matchups_created,
        "matchups_updated": matchups_updated
    }