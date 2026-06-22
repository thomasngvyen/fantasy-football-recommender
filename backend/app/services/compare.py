from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.tables import Matchup, Player, Projection
from app.models import (
    ComparePlayerResult,
    CompareRequest,
    CompareResponse,
    PlayerOut,
    ProjectionBreakdown,
)


def get_player_by_sleeper_id(db: Session, sleeper_id: str) -> Player:
    player = db.execute(
        select(Player).where(Player.sleeper_id == sleeper_id)
    ).scalar_one_or_none()
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player not found: {sleeper_id}",
        )
    return player


def _load_matchup_and_projection(
    db: Session, player: Player, week: int, season: int
) -> tuple[Matchup, Projection]:
    matchup = db.execute(
        select(Matchup)
        .where(
            Matchup.player_id == player.id,
            Matchup.week == week,
            Matchup.season == season,
        )
        .options(selectinload(Matchup.projection))
    ).scalar_one_or_none()

    if matchup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No matchup for {player.name} in season {season} week {week}. "
                "Run sync_week.py first."
            ),
        )

    if matchup.projection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No cached projection for {player.name} in season {season} week {week}. "
                "Run sync_week.py with projections enabled."
            ),
        )

    return matchup, matchup.projection


def _build_explanation(
    player: Player, matchup: Matchup, breakdown: ProjectionBreakdown
) -> str:
    """Short human-readable summary from the cached breakdown."""
    parts: list[str] = []

    if breakdown.home_advantage_modifier > 0:
        parts.append(f"home boost (+{breakdown.home_advantage_modifier:.2f})")
    elif breakdown.home_advantage_modifier < 0:
        parts.append(f"away ({breakdown.home_advantage_modifier:.2f})")

    if breakdown.defense_rank_modifier > 0:
        parts.append(
            f"favorable matchup vs {matchup.opponent} "
            f"(+{breakdown.defense_rank_modifier:.2f})"
        )
    elif breakdown.defense_rank_modifier < 0:
        parts.append(
            f"tough matchup vs {matchup.opponent} "
            f"({breakdown.defense_rank_modifier:.2f})"
        )

    if breakdown.total_offense_rank_modifier != 0:
        parts.append(
            f"opponent offense ({breakdown.total_offense_rank_modifier:+.2f})"
        )

    if breakdown.weather_modifier < 0:
        parts.append(f"weather ({breakdown.weather_modifier:.2f})")
    elif breakdown.weather_notes:
        parts.append(breakdown.weather_notes.lower())

    modifier_text = ", ".join(parts) if parts else "neutral matchup factors"
    home_away = "home" if matchup.is_home else "away"
    return (
        f"{player.name} ({player.position}) projects {breakdown.final_projection:.2f} "
        f"pts {home_away} vs {matchup.opponent}: {modifier_text}."
    )


def _to_compare_player_result(
    player: Player, matchup: Matchup, projection: Projection
) -> ComparePlayerResult:
    breakdown = ProjectionBreakdown.model_validate(projection.breakdown_json)
    return ComparePlayerResult(
        sleeper_id=player.sleeper_id,
        name=player.name,
        position=player.position,
        team=player.team,
        opponent=matchup.opponent,
        adjusted_points=projection.adjusted_points,
        breakdown=breakdown,
        explanation=_build_explanation(player, matchup, breakdown),
    )


def compare_players(db: Session, request: CompareRequest) -> CompareResponse:
    player_a = get_player_by_sleeper_id(db, request.player_a_id)
    player_b = get_player_by_sleeper_id(db, request.player_b_id)

    if player_a.position != player_b.position:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot compare {player_a.position} ({player_a.name}) "
                f"with {player_b.position} ({player_b.name})."
            ),
        )

    matchup_a, projection_a = _load_matchup_and_projection(
        db, player_a, request.week, request.season
    )
    matchup_b, projection_b = _load_matchup_and_projection(
        db, player_b, request.week, request.season
    )

    result_a = _to_compare_player_result(player_a, matchup_a, projection_a)
    result_b = _to_compare_player_result(player_b, matchup_b, projection_b)

    if result_a.adjusted_points >= result_b.adjusted_points:
        winner, loser = result_a, result_b
    else:
        winner, loser = result_b, result_a

    margin = round(winner.adjusted_points - loser.adjusted_points, 2)

    if margin == 0:
        recommendation = (
            f"It's a tie — {winner.name} and {loser.name} both project "
            f"{winner.adjusted_points:.2f} points."
        )
    else:
        recommendation = (
            f"Start {winner.name} over {loser.name} "
            f"by {margin:.2f} projected points."
        )

    return CompareResponse(
        week=request.week,
        season=request.season,
        winner=winner,
        loser=loser,
        margin_of_victory=margin,
        recommendation=recommendation,
    )


def list_players(db: Session, *, position: str | None = None) -> list[PlayerOut]:
    query = select(Player).order_by(Player.name)
    if position is not None:
        query = query.where(Player.position == position.upper())

    players = db.scalars(query).all()
    return [
        PlayerOut(
            sleeper_id=player.sleeper_id,
            name=player.name,
            position=player.position,
            team=player.team,
        )
        for player in players
    ]
