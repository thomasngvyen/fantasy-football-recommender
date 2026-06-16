from app.services.base_projections import (
    BACKUP_QB_BASE,
    is_depth_chart_backup,
    resolve_base_projection,
)


def test_is_depth_chart_backup_qb2():
    player = {
        "team": "NYG",
        "depth_chart_position": "QB",
        "depth_chart_order": 2,
    }
    assert is_depth_chart_backup(player, "QB") is True


def test_is_depth_chart_backup_starter_qb():
    player = {
        "team": "NYG",
        "depth_chart_position": "QB",
        "depth_chart_order": 1,
    }
    assert is_depth_chart_backup(player, "QB") is False


def test_is_depth_chart_backup_missing_order():
    player = {"team": "NYG", "depth_chart_position": "QB"}
    assert is_depth_chart_backup(player, "QB") is False


def test_is_depth_chart_backup_ignores_non_qb_positions():
    player = {
        "team": "KC",
        "depth_chart_position": "LWR",
        "depth_chart_order": 2,
    }
    assert is_depth_chart_backup(player, "WR") is False


def test_resolve_base_projection_keeps_season_average_for_wr2():
    sleeper_player = {
        "team": "KC",
        "depth_chart_position": "LWR",
        "depth_chart_order": 2,
    }
    base = resolve_base_projection(
        sleeper_id="9999",
        position="WR",
        season_averages={"9999": 11.5},
        sleeper_player=sleeper_player,
    )
    assert base == 11.5


def test_resolve_base_projection_uses_backup_baseline_for_qb2():
    sleeper_player = {
        "team": "NYG",
        "depth_chart_position": "QB",
        "depth_chart_order": 2,
    }
    base = resolve_base_projection(
        sleeper_id="2306",
        position="QB",
        season_averages={"2306": 22.39},
        sleeper_player=sleeper_player,
    )
    assert base == BACKUP_QB_BASE


def test_resolve_base_projection_uses_season_average_for_starter():
    sleeper_player = {
        "team": "KC",
        "depth_chart_position": "QB",
        "depth_chart_order": 1,
    }
    base = resolve_base_projection(
        sleeper_id="4881",
        position="QB",
        season_averages={"4881": 21.16},
        sleeper_player=sleeper_player,
    )
    assert base == 21.16
