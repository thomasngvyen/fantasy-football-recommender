import json
from pathlib import Path

import pytest

from app.services.projection import compute_adjusted_projection

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures"
MOCK_SCENARIOS = json.loads((FIXTURES_DIR / "mock_scenarios.json").read_text())

SCENARIO_DEFAULTS = {
    "defense_rank_passing": 16,
    "defense_rank_run": 16,
    "total_offense_rank": 16,
}

OFFENSIVE_POSITIONS = frozenset({"QB", "WR", "TE", "RB"})
DEFENSE_POSITIONS = frozenset({"D", "DST"})

BREAKDOWN_KEYS = {
    "base_projection",
    "home_advantage_modifier",
    "defense_rank_modifier",
    "total_offense_rank_modifier",
    "weather_modifier",
    "final_projection",
}


def _scenario_kwargs(scenario: dict) -> dict:
    kwargs = {**SCENARIO_DEFAULTS, **scenario}
    kwargs.pop("name", None)
    return kwargs


def _relevant_defense_rank(scenario: dict) -> int | None:
    position = scenario["position"]
    passing = scenario.get("defense_rank_passing", SCENARIO_DEFAULTS["defense_rank_passing"])
    run = scenario.get("defense_rank_run", SCENARIO_DEFAULTS["defense_rank_run"])

    if position in {"QB", "WR"}:
        return passing
    if position == "TE":
        return round(passing * 0.7 + run * 0.3)
    if position == "RB":
        return run
    return None


@pytest.mark.parametrize("scenario", MOCK_SCENARIOS, ids=[s["name"] for s in MOCK_SCENARIOS])
def test_mock_scenario_projection(scenario: dict) -> None:
    final_projection, breakdown = compute_adjusted_projection(**_scenario_kwargs(scenario))

    assert BREAKDOWN_KEYS.issubset(breakdown.keys())
    assert breakdown["final_projection"] == final_projection
    assert breakdown["base_projection"] == scenario["base"]
    assert final_projection >= 0.0

    is_home = scenario["is_home"]
    is_dome = scenario["is_dome"]
    position = scenario["position"]
    wind_mph = scenario.get("wind_mph", 0.0)
    rain = scenario.get("rain", False)

    if is_dome:
        assert breakdown["weather_modifier"] == 0.0
        assert breakdown.get("weather_notes") == "Dome game, no wind or rain"
    elif wind_mph <= 10 and not rain:
        assert breakdown["weather_modifier"] == 0.0

    if is_home:
        assert breakdown["home_advantage_modifier"] > 0.0
    else:
        assert breakdown["home_advantage_modifier"] == 0.0

    if position in DEFENSE_POSITIONS:
        assert breakdown["defense_rank_modifier"] == 0.0
        offense_rank = scenario.get(
            "total_offense_rank", SCENARIO_DEFAULTS["total_offense_rank"]
        )
        if offense_rank < 16:
            assert breakdown["total_offense_rank_modifier"] < 0.0
        elif offense_rank > 16:
            assert breakdown["total_offense_rank_modifier"] > 0.0
        else:
            assert breakdown["total_offense_rank_modifier"] == pytest.approx(0.0, abs=0.1)
    elif position == "K":
        assert breakdown["defense_rank_modifier"] == 0.0
        assert breakdown["total_offense_rank_modifier"] == 0.0
        if not is_dome and (wind_mph > 10 or rain):
            assert breakdown["weather_modifier"] < 0.0
    else:
        assert breakdown["total_offense_rank_modifier"] == 0.0
        defense_rank = _relevant_defense_rank(scenario)
        assert defense_rank is not None

        if defense_rank < 16:
            assert breakdown["defense_rank_modifier"] < 0.0
        elif defense_rank > 16:
            assert breakdown["defense_rank_modifier"] > 0.0
        else:
            assert breakdown["defense_rank_modifier"] == pytest.approx(0.0, abs=0.1)

        if not is_dome and rain and position in {"QB", "WR", "TE", "K"}:
            assert breakdown["weather_modifier"] < 0.0
        if not is_dome and rain and position == "RB":
            assert breakdown["weather_modifier"] > 0.0
        if not is_dome and wind_mph > 10 and position in {"QB", "WR", "TE", "K"}:
            assert breakdown["weather_modifier"] < 0.0


def test_all_mock_scenarios_are_covered() -> None:
    assert len(MOCK_SCENARIOS) == 96
    assert len({s["name"] for s in MOCK_SCENARIOS}) == 96
