import math

POSITION_DEFENSE_WEIGHT: dict[str, float] = {
    "QB": 0.14,
    "WR": 0.16,
    "TE": 0.11,
    "RB": 0.09,
    "K": 0.0,
    "D": 0.0,
    "DST": 0.0,
}

WIND_SENSITIVITY: dict[str, float] = {
    "QB": 0.08,
    "WR": 0.08,
    "TE": 0.05,
    "RB": 0.02,
    "K": 0.10,
    "D": 0.0,
    "DST": 0.0,
}

RAIN_EFFECT: dict[str, float] = {
    "QB": -0.03,
    "WR": -0.03,
    "TE": -0.02,
    "RB": 0.01,
    "K": -0.04,
    "D": 0.0,
    "DST": 0.0,
}

HOME_BONUS = 0.05
DST_OFFENSE_WEIGHT = 0.15
TE_PASS_BLEND = 0.7
TE_RUN_BLEND = 0.3

DEFENSE_POSITIONS = frozenset({"D", "DST"})


def _rank_modifier(rank: int, weight: float) -> float:
    """Higher rank (worse defense) boosts offensive projections."""
    normalized = (rank - 16.5) / 15.5
    curved = math.copysign(abs(normalized) ** 1.3, normalized)
    return curved * weight


def _wind_penalty(wind_mph: float, sensitivity: float) -> float:
    if wind_mph <= 10:
        return 0.0
    ramp = min(1.0, (wind_mph - 10) / 15)
    return -ramp * sensitivity


def _relevant_defense_rank(
    position: str,
    defense_rank_passing: int,
    defense_rank_run: int,
) -> int | None:
    if position in {"QB", "WR"}:
        return defense_rank_passing
    if position == "TE":
        return round(defense_rank_passing * TE_PASS_BLEND + defense_rank_run * TE_RUN_BLEND)
    if position == "RB":
        return defense_rank_run
    return None


def _apply_multiplier(
    base: float,
    multiplier: float,
    modifier_pct: float,
) -> tuple[float, float]:
    before = base * multiplier
    multiplier *= 1.0 + modifier_pct
    after = base * multiplier
    return multiplier, round(after - before, 2)


def compute_adjusted_projection(
    base: float,
    position: str,
    is_home: bool,
    defense_rank_passing: int,
    defense_rank_run: int,
    total_offense_rank: int,
    wind_mph: float,
    is_dome: bool,
    rain: bool,
) -> tuple[float, dict]:
    breakdown: dict = {
        "base_projection": base,
        "home_advantage_modifier": 0.0,
        "defense_rank_modifier": 0.0,
        "total_offense_rank_modifier": 0.0,
        "weather_modifier": 0.0,
        "final_projection": 0.0,
    }

    multiplier = 1.0

    if is_dome:
        wind_mph = 0.0
        rain = False
        breakdown["weather_notes"] = "Dome game, no wind or rain"
    else:
        weather_pct = 0.0
        weather_pct += _wind_penalty(wind_mph, WIND_SENSITIVITY.get(position, 0.0))
        if rain:
            weather_pct += RAIN_EFFECT.get(position, 0.0)

        multiplier, breakdown["weather_modifier"] = _apply_multiplier(
            base, multiplier, weather_pct
        )

    if is_home:
        multiplier, breakdown["home_advantage_modifier"] = _apply_multiplier(
            base, multiplier, HOME_BONUS
        )

    if position in DEFENSE_POSITIONS:
        offense_pct = _rank_modifier(total_offense_rank, DST_OFFENSE_WEIGHT)
        multiplier, breakdown["total_offense_rank_modifier"] = _apply_multiplier(
            base, multiplier, offense_pct
        )
    else:
        defense_rank = _relevant_defense_rank(
            position, defense_rank_passing, defense_rank_run
        )
        if defense_rank is not None:
            defense_weight = POSITION_DEFENSE_WEIGHT.get(position, 0.0)
            defense_pct = _rank_modifier(defense_rank, defense_weight)
            multiplier, breakdown["defense_rank_modifier"] = _apply_multiplier(
                base, multiplier, defense_pct
            )

    final_projection = max(0.0, round(base * multiplier, 2))
    breakdown["final_projection"] = final_projection

    return final_projection, breakdown
