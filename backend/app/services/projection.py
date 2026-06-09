def compute_adjusted_projection(
    base: float,
    position: str,
    is_home: bool,
    defense_rank_passing: int,
    defense_rank_run: int,
    wind_mph: float,
    is_dome: bool,
    rain: bool,
) -> tuple[float, dict]:
