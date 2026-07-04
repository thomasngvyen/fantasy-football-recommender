from __future__ import annotations

import json

from app.services.matchup_builder import schedule_path_for_week

NFL_TEAM_COUNT = 32


def week_schedule_info(week: int) -> dict | None:
    """Return fixture metadata for a week, or None when no schedule file exists."""
    path = schedule_path_for_week(week)
    if not path.exists():
        return None

    games = json.loads(path.read_text(encoding="utf-8"))
    teams = sorted({row["team"] for row in games})
    team_count = len(teams)
    game_count = len(games) // 2

    return {
        "week": week,
        "game_count": game_count,
        "teams_playing": team_count,
        "teams_on_bye": sorted(_teams_on_bye(teams)),
        "has_schedule": True,
    }


def list_week_schedules(*, start: int = 1, end: int = 17) -> list[dict]:
    weeks: list[dict] = []
    for week in range(start, end + 1):
        info = week_schedule_info(week)
        if info is not None:
            weeks.append(info)
    return weeks


def _teams_on_bye(teams_playing: list[str]) -> set[str]:
    from app.services.sleeper_client import NFL_TEAM_CODES

    playing = {team.upper() for team in teams_playing}
    return {team for team in NFL_TEAM_CODES if team not in playing}
