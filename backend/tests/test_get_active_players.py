from app.services.sleeper_client import SleeperClient


def test_get_active_players_excludes_retired(monkeypatch):
    roster = {
        "389": {
            "player_id": "389",
            "first_name": "Matt",
            "last_name": "Cassel",
            "team": None,
            "status": "Inactive",
            "active": False,
            "fantasy_positions": ["QB"],
        },
        "4881": {
            "player_id": "4881",
            "first_name": "Patrick",
            "last_name": "Mahomes",
            "team": "KC",
            "status": "Active",
            "active": True,
            "fantasy_positions": ["QB"],
            "depth_chart_order": 1,
            "depth_chart_position": "QB",
        },
    }

    monkeypatch.setattr(
        SleeperClient,
        "get_all_players",
        lambda self, *, refresh=False: roster,
    )

    client = SleeperClient()
    active = client.get_active_players(position="QB")

    assert len(active) == 1
    assert active[0]["name"] == "Patrick Mahomes"
