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


def test_get_active_players_includes_dst(monkeypatch):
    roster = {
        "KC": {
            "player_id": "KC",
            "first_name": "Kansas City",
            "last_name": "Chiefs",
            "team": "KC",
            "status": None,
            "active": True,
            "position": "DEF",
            "fantasy_positions": ["DEF"],
        },
    }

    monkeypatch.setattr(
        SleeperClient,
        "get_all_players",
        lambda self, *, refresh=False: roster,
    )

    client = SleeperClient()
    dst = client.get_active_players(position="DST")

    assert len(dst) == 1
    assert dst[0]["position"] == "DST"
    assert dst[0]["name"] == "Kansas City Chiefs"
