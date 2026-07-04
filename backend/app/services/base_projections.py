from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

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

BACKUP_QB_BASE = 6.0
DST_RANK_SPREAD = 3.0
DEFENSE_POSITIONS = frozenset({"DST", "D"})

STATS_BASE_URL = "https://api.sleeper.app/v1/stats/nfl/regular"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFENSE_RANKS_PATH = FIXTURES_DIR / "defense_ranks.json"


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


def load_defense_ranks_by_team(path: Path | None = None) -> dict[str, dict]:
    """Load defense_ranks.json keyed by team abbreviation."""
    ranks_path = path or DEFENSE_RANKS_PATH
    rows = json.loads(ranks_path.read_text(encoding="utf-8"))
    return {row["team"]: row for row in rows}


def dst_base_from_defense_ranks(defense_row: dict) -> float:
    """
    Estimate weekly DST fantasy points from pass/run defense ranks.

    Lower ranks (better defense) produce a higher base. Centered around the
    DST default (8.0) with roughly +/- 3 points for elite vs weak units.
    """
    avg_rank = (defense_row["pass_defense_rank"] + defense_row["run_defense_rank"]) / 2
    normalized = (16.5 - avg_rank) / 15.5
    base = DEFAULT_BASE_BY_POSITION["DST"] + normalized * DST_RANK_SPREAD

    pass_avg = defense_row.get("points_allowed_pass_avg")
    run_avg = defense_row.get("points_allowed_run_avg")
    if pass_avg is not None and run_avg is not None:
        # Lower fantasy points allowed to skill players -> stronger DST baseline.
        base += (15.5 - (pass_avg + run_avg)) * 0.12

    return round(max(0.0, base), 2)


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
    defense_ranks_by_team: dict[str, dict] | None = None,
) -> float:
    """
    Prefer last-season per-game average when available.

    Backup QBs on the current NFL depth chart use a low baseline instead of prior
    starter production (e.g. a QB who started briefly last season but is now QB2).

    DST units use defense_ranks.json because Sleeper season stats are keyed by
    numeric player IDs, not team abbreviations like "KC" or "JAX".

    If season averages were loaded but a player has no recorded games, fall back
    to the position default (e.g. kickers without prior-season stats).
    """
    if is_depth_chart_backup(sleeper_player, position):
        return BACKUP_QB_BASE

    if position in DEFENSE_POSITIONS:
        team = (sleeper_player or {}).get("team") or sleeper_id
        if defense_ranks_by_team and team in defense_ranks_by_team:
            return dst_base_from_defense_ranks(defense_ranks_by_team[team])
        return DEFAULT_BASE_BY_POSITION.get(position, 0.0)

    if season_averages is not None:
        if sleeper_id in season_averages:
            return season_averages[sleeper_id]
        return DEFAULT_BASE_BY_POSITION.get(position, 0.0)
    return DEFAULT_BASE_BY_POSITION.get(position, 0.0)
