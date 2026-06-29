from app.services.base_projections import (
    BACKUP_QB_BASE,
    DEFAULT_BASE_BY_POSITION,
    dst_base_from_defense_ranks,
    is_depth_chart_backup,
    load_defense_ranks_by_team,
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


def test_resolve_base_projection_uses_defense_ranks_for_dst():
    defense_ranks = load_defense_ranks_by_team()
    base = resolve_base_projection(
        sleeper_id="JAX",
        position="DST",
        season_averages={"JAX": 0.0},
        sleeper_player={"team": "JAX", "position": "DEF"},
        defense_ranks_by_team=defense_ranks,
    )
    assert base == dst_base_from_defense_ranks(defense_ranks["JAX"])
    assert base > DEFAULT_BASE_BY_POSITION["DST"]


def test_resolve_base_projection_dst_without_ranks_uses_default():
    base = resolve_base_projection(
        sleeper_id="JAX",
        position="DST",
        season_averages={"JAX": 0.0},
        sleeper_player={"team": "JAX"},
        defense_ranks_by_team=None,
    )
    assert base == DEFAULT_BASE_BY_POSITION["DST"]


def test_dst_base_from_defense_ranks_elite_beats_weak():
    defense_ranks = load_defense_ranks_by_team()
    elite = dst_base_from_defense_ranks(defense_ranks["HOU"])
    weak = dst_base_from_defense_ranks(defense_ranks["NYJ"])
    assert elite > weak
