from app.services.sleeper_client import (
    is_active_sleeper_player,
    is_on_nfl_roster,
    is_rosterable_fantasy_player,
)


def test_excludes_free_agent_without_team():
    player = {
        "team": None,
        "status": "Active",
        "depth_chart_order": 1,
        "depth_chart_position": "QB",
    }
    assert is_rosterable_fantasy_player(player, "QB") is False


def test_excludes_empty_team_string():
    player = {
        "team": "   ",
        "status": "Active",
        "depth_chart_order": 1,
        "depth_chart_position": "QB",
    }
    assert is_on_nfl_roster(player) is False
    assert is_rosterable_fantasy_player(player, "QB") is False


def test_excludes_legacy_team_code():
    player = {
        "team": "OAK",
        "status": "Active",
        "depth_chart_order": 1,
        "depth_chart_position": "QB",
    }
    assert is_on_nfl_roster(player) is False
    assert is_rosterable_fantasy_player(player, "QB") is False


def test_includes_current_nfl_team():
    player = {"team": "LV", "status": "Active"}
    assert is_on_nfl_roster(player) is True


def test_excludes_inactive_flag():
    player = {
        "team": "KC",
        "status": "Active",
        "active": False,
        "depth_chart_order": 1,
        "depth_chart_position": "QB",
    }
    assert is_rosterable_fantasy_player(player, "QB") is False


def test_excludes_matt_cassel_profile():
    cassel = {
        "team": None,
        "status": "Inactive",
        "active": False,
        "depth_chart_order": None,
        "depth_chart_position": None,
        "fantasy_positions": ["QB"],
        "player_id": "389",
        "first_name": "Matt",
        "last_name": "Cassel",
    }
    assert is_active_sleeper_player(cassel) is False
    assert is_rosterable_fantasy_player(cassel, "QB") is False


def test_excludes_qb3():
    player = {
        "team": "TEN",
        "status": "Active",
        "depth_chart_order": 3,
        "depth_chart_position": "QB",
    }
    assert is_rosterable_fantasy_player(player, "QB") is False


def test_includes_qb2():
    player = {
        "team": "NYG",
        "status": "Active",
        "depth_chart_order": 2,
        "depth_chart_position": "QB",
    }
    assert is_rosterable_fantasy_player(player, "QB") is True


def test_excludes_wr5():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 5,
        "depth_chart_position": "SWR",
    }
    assert is_rosterable_fantasy_player(player, "WR") is False


def test_excludes_wr4():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 4,
        "depth_chart_position": "LWR",
    }
    assert is_rosterable_fantasy_player(player, "WR") is False


def test_includes_wr3():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 3,
        "depth_chart_position": "SWR",
    }
    assert is_rosterable_fantasy_player(player, "WR") is True


def test_excludes_rb3():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 3,
        "depth_chart_position": "RB",
    }
    assert is_rosterable_fantasy_player(player, "RB") is False


def test_includes_rb2():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 2,
        "depth_chart_position": "RB",
    }
    assert is_rosterable_fantasy_player(player, "RB") is True


def test_excludes_te3():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 3,
        "depth_chart_position": "TE",
    }
    assert is_rosterable_fantasy_player(player, "TE") is False


def test_includes_te2():
    player = {
        "team": "KC",
        "status": "Active",
        "depth_chart_order": 2,
        "depth_chart_position": "TE",
    }
    assert is_rosterable_fantasy_player(player, "TE") is True


def test_kicker_only_requires_team_and_status():
    player = {"team": "KC", "status": "Active"}
    assert is_rosterable_fantasy_player(player, "K") is True
