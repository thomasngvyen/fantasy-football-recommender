from __future__ import annotations


class AlwaysRosterableSleeper:
    """Test double that treats every Sleeper ID as rosterable."""

    def get_player_record(self, player_id: str, *, refresh: bool = False) -> dict:
        del refresh
        return {
            "sleeper_id": player_id,
            "name": player_id,
            "position": "QB",
            "team": "KC",
        }
