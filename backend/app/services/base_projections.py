from __future__ import annotations

from collections import defaultdict

import httpx

SCORING_FIELDS = {
    "half_ppr": "pts_half_ppr",
    "ppr": "pts_ppr",
    "std": "pts_std",
}

DEFAULT_BASE_BY_POSITION: dict[str, float] = {
    "QB": 18.0,
    "RB": 12.0,
    "WR": 12.0,
    "TE": 8.0,
    "K": 8.0,
    "DST": 8.0,
    "D": 8.0,
}

BACKUP_QB_BASE = 0.0

STATS_BASE_URL = "https://api.sleeper.app/v1/stats/nfl/regular"


def fetch_season_averages(
    season: int,
    *,
    scoring: str = "half_ppr",
    max_week: int = 18,
    timeout: float = 30.0,
) -> dict[str, float]:
    """
    Compute per-game fantasy averages from Sleeper weekly stats.

    Returns a map of sleeper player_id -> average points per active week.
    """
    points_field = SCORING_FIELDS.get(scoring, "pts_half_ppr")
    totals: dict[str, float] = defaultdict(float)
    games: dict[str, int] = defaultdict(int)

    with httpx.Client(timeout=timeout) as client:
        for week in range(1, max_week + 1):
            response = client.get(f"{STATS_BASE_URL}/{season}/{week}")
            if response.status_code != 200:
                continue

            for player_id, stats in response.json().items():
                if stats.get("gms_active", 0) <= 0:
                    continue

                points = stats.get(points_field)
                if points is None:
                    points = stats.get("pts_ppr") or 0.0
                if points <= 0:
                    continue

                pid = str(player_id)
                totals[pid] += float(points)
                games[pid] += 1

    return {
        player_id: round(totals[player_id] / games[player_id], 2)
        for player_id in totals
        if games[player_id] > 0
    }


def is_depth_chart_backup(sleeper_player: dict | None, position: str) -> bool:
    """
    True when Sleeper lists the player as QB2+ on the current depth chart.

    Only QBs are treated as backups here; WR/RB/TE depth often still play
    meaningful snaps, unlike backup quarterbacks who rarely see the field.
    """
    if position != "QB":
        return False
    if not sleeper_player or not sleeper_player.get("team"):
        return False

    order = sleeper_player.get("depth_chart_order")
    if order is None or int(order) <= 1:
        return False

    return sleeper_player.get("depth_chart_position") == "QB"


def resolve_base_projection(
    *,
    sleeper_id: str,
    position: str,
    season_averages: dict[str, float] | None = None,
    sleeper_player: dict | None = None,
) -> float:
    """
    Prefer last-season per-game average when available.

    Backup QBs on the current NFL depth chart use a low baseline instead of prior
    starter production (e.g. a QB who started briefly last season but is now QB2).

    If season averages were loaded but a player has no recorded games,
    return 0.0 instead of a generic starter baseline.
    """
    if is_depth_chart_backup(sleeper_player, position):
        return BACKUP_QB_BASE

    if season_averages is not None:
        return season_averages.get(sleeper_id, 0.0)
    return DEFAULT_BASE_BY_POSITION.get(position, 0.0)
