from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

BASE_URL = "https://api.sleeper.app/v1"
FANTASY_POSITIONS = frozenset({"QB", "RB", "WR", "TE", "K", "DEF"})
POSITION_MAP = {"DEF": "DST"}
ROSTERABLE_STATUSES = frozenset({"Active", "Questionable", "Doubtful"})
NFL_TEAM_CODES = frozenset({
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN",
    "DET", "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA",
    "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB",
    "TEN", "WAS",
})
MAX_DEPTH_ORDER_BY_POSITION = {
    "QB": 2,
    "RB": 2,
    "WR": 3,
    "TE": 2,
}
WR_DEPTH_CHART_POSITIONS = frozenset({"LWR", "RWR", "SWR"})


@dataclass(frozen=True)
class NFLState:
    week: int
    season: int
    season_type: str
    display_week: int
    league_season: str
    previous_season: str


@dataclass
class SleeperClient:
    timeout: float = 30.0
    _players_cache: dict[str, dict] | None = None

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(base_url=BASE_URL, timeout=self.timeout) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def get_nfl_state(self) -> NFLState:
        """Current NFL week and season from Sleeper."""
        data = self._get("/state/nfl")
        return NFLState(
            week=int(data["week"]),
            season=int(data["season"]),
            season_type=data["season_type"],
            display_week=int(data["display_week"]),
            league_season=str(data["league_season"]),
            previous_season=str(data["previous_season"]),
        )

    def get_all_players(self, *, refresh: bool = False) -> dict[str, dict]:
        """
        Full NFL player map keyed by Sleeper player_id.

        Sleeper recommends caching this response (about 5MB) and refreshing
        at most once per day.
        """
        if self._players_cache is None or refresh:
            raw = self._get("/players/nfl")
            self._players_cache = {str(player_id): player for player_id, player in raw.items()}
        return self._players_cache

    def get_player(self, player_id: str, *, refresh: bool = False) -> dict | None:
        """Fetch one player by Sleeper player_id."""
        players = self.get_all_players(refresh=refresh)
        return players.get(str(player_id))

    def get_players(
        self, player_ids: list[str], *, refresh: bool = False
    ) -> dict[str, dict]:
        """Fetch multiple players by Sleeper player_id."""
        players = self.get_all_players(refresh=refresh)
        return {
            str(player_id): players[str(player_id)]
            for player_id in player_ids
            if str(player_id) in players
        }

    def to_player_record(self, sleeper_player: dict) -> dict | None:
        """Map a Sleeper player payload to Player table fields."""
        fantasy_positions = sleeper_player.get("fantasy_positions") or []
        position = (
            fantasy_positions[0]
            if fantasy_positions
            else sleeper_player.get("position")
        )
        if position not in FANTASY_POSITIONS:
            return None
        if sleeper_player.get("status") not in ROSTERABLE_STATUSES:
            return None

        first_name = sleeper_player.get("first_name", "")
        last_name = sleeper_player.get("last_name", "")
        mapped_position = POSITION_MAP.get(position, position)

        if not is_rosterable_fantasy_player(sleeper_player, mapped_position):
            return None

        return {
            "sleeper_id": str(sleeper_player["player_id"]),
            "name": f"{first_name} {last_name}".strip(),
            "position": mapped_position,
            "team": sleeper_player.get("team"),
            "base_projection": 0.0,
        }

    def get_active_players(
        self,
        *,
        position: str | None = None,
        refresh: bool = False,
    ) -> list[dict]:
        """
        Normalized player records for currently rostered, fantasy-relevant players.

        Excludes free agents, retired/inactive players, and deep backups.
        """
        mapped_position = POSITION_MAP.get(position, position) if position else None
        records: list[dict] = []

        for player in self.get_all_players(refresh=refresh).values():
            record = self.to_player_record(player)
            if record is None:
                continue
            if mapped_position and record["position"] != mapped_position:
                continue
            records.append(record)

        return sorted(records, key=lambda row: row["name"])

    def get_player_records(self, *, refresh: bool = False) -> list[dict]:
        """All active Sleeper players normalized for the Player table."""
        return self.get_active_players(refresh=refresh)

    def get_player_record(self, player_id: str, *, refresh: bool = False) -> dict | None:
        """One player normalized for the Player table."""
        player = self.get_player(player_id, refresh=refresh)
        if player is None:
            return None
        return self.to_player_record(player)

    def clear_cache(self) -> None:
        """Drop the in-memory player cache."""
        self._players_cache = None


def is_rosterable_fantasy_player(sleeper_player: dict, position: str) -> bool:
    """
    True for active rostered players within fantasy-relevant depth chart slots.

    Excludes free agents, inactive/retired players, and deep backups (QB3+, RB3+, WR4+, TE3+).
    """
    if not is_active_sleeper_player(sleeper_player):
        return False

    if position in {"K", "DST", "D"}:
        return True

    order = sleeper_player.get("depth_chart_order")
    if order is None:
        return False

    max_order = MAX_DEPTH_ORDER_BY_POSITION.get(position)
    if max_order is not None and int(order) > max_order:
        return False

    chart_pos = sleeper_player.get("depth_chart_position")
    if position == "QB":
        return chart_pos == "QB"
    if position == "RB":
        return chart_pos == "RB"
    if position == "TE":
        return chart_pos == "TE"
    if position == "WR":
        return chart_pos in WR_DEPTH_CHART_POSITIONS
    return True


def is_on_nfl_roster(sleeper_player: dict) -> bool:
    """True when Sleeper assigns the player to a current NFL team abbreviation."""
    team = sleeper_player.get("team")
    if not team or not str(team).strip():
        return False
    return str(team).upper() in NFL_TEAM_CODES


def is_active_sleeper_player(sleeper_player: dict) -> bool:
    """True when Sleeper marks the player as on a roster and fantasy-relevant."""
    if not is_on_nfl_roster(sleeper_player):
        return False
    if sleeper_player.get("active") is False:
        return False
    if sleeper_player.get("status") not in ROSTERABLE_STATUSES:
        return False
    return True
