from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.tables import Base, Matchup, Player, Projection
from app.models import CompareRequest
from app.services.compare import compare_players


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed_compare_fixtures(session: Session) -> tuple[Player, Player]:
    player_a = Player(
        sleeper_id="qb-a",
        name="Alpha QB",
        position="QB",
        team="KC",
        base_projection=20.0,
    )
    player_b = Player(
        sleeper_id="qb-b",
        name="Beta QB",
        position="QB",
        team="BUF",
        base_projection=18.0,
    )
    session.add_all([player_a, player_b])
    session.flush()

    matchup_a = Matchup(
        player_id=player_a.id,
        week=1,
        season=2026,
        opponent="BAL",
        is_home=True,
        is_dome=False,
        game_datetime=datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
    )
    matchup_b = Matchup(
        player_id=player_b.id,
        week=1,
        season=2026,
        opponent="MIA",
        is_home=False,
        is_dome=False,
        game_datetime=datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
    )
    session.add_all([matchup_a, matchup_b])
    session.flush()

    breakdown_a = {
        "base_projection": 20.0,
        "home_advantage_modifier": 1.0,
        "defense_rank_modifier": 0.5,
        "total_offense_rank_modifier": 0.0,
        "weather_modifier": 0.0,
        "final_projection": 21.5,
    }
    breakdown_b = {
        "base_projection": 18.0,
        "home_advantage_modifier": 0.0,
        "defense_rank_modifier": -0.3,
        "total_offense_rank_modifier": 0.0,
        "weather_modifier": -0.2,
        "final_projection": 17.5,
    }

    session.add_all(
        [
            Projection(
                player_id=player_a.id,
                matchup_id=matchup_a.id,
                week=1,
                season=2026,
                adjusted_points=21.5,
                breakdown_json=breakdown_a,
            ),
            Projection(
                player_id=player_b.id,
                matchup_id=matchup_b.id,
                week=1,
                season=2026,
                adjusted_points=17.5,
                breakdown_json=breakdown_b,
            ),
        ]
    )
    session.commit()
    return player_a, player_b


def test_compare_players_picks_higher_projection(db_session: Session):
    _seed_compare_fixtures(db_session)

    response = compare_players(
        db_session,
        CompareRequest(
            player_a_id="qb-a",
            player_b_id="qb-b",
            week=1,
            season=2026,
        ),
    )

    assert response.winner.sleeper_id == "qb-a"
    assert response.loser.sleeper_id == "qb-b"
    assert response.margin_of_victory == 4.0
    assert response.winner.breakdown.final_projection == 21.5
    assert "Start Alpha QB over Beta QB" in response.recommendation


def test_compare_players_rejects_position_mismatch(db_session: Session):
    player_qb = Player(
        sleeper_id="qb-1",
        name="Some QB",
        position="QB",
        team="KC",
        base_projection=20.0,
    )
    player_rb = Player(
        sleeper_id="rb-1",
        name="Some RB",
        position="RB",
        team="KC",
        base_projection=12.0,
    )
    db_session.add_all([player_qb, player_rb])
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        compare_players(
            db_session,
            CompareRequest(
                player_a_id="qb-1",
                player_b_id="rb-1",
                week=1,
                season=2026,
            ),
        )

    assert exc.value.status_code == 400


def test_compare_players_missing_projection(db_session: Session):
    player_a = Player(
        sleeper_id="no-proj",
        name="No Proj QB",
        position="QB",
        team="KC",
        base_projection=20.0,
    )
    player_b = Player(
        sleeper_id="has-proj",
        name="Has Proj QB",
        position="QB",
        team="BUF",
        base_projection=18.0,
    )
    db_session.add_all([player_a, player_b])
    db_session.flush()

    matchup_a = Matchup(
        player_id=player_a.id,
        week=1,
        season=2026,
        opponent="BAL",
        is_home=True,
        is_dome=False,
        game_datetime=datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
    )
    matchup_b = Matchup(
        player_id=player_b.id,
        week=1,
        season=2026,
        opponent="MIA",
        is_home=False,
        is_dome=False,
        game_datetime=datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([matchup_a, matchup_b])
    db_session.flush()
    db_session.add(
        Projection(
            player_id=player_b.id,
            matchup_id=matchup_b.id,
            week=1,
            season=2026,
            adjusted_points=17.5,
            breakdown_json={
                "base_projection": 18.0,
                "home_advantage_modifier": 0.0,
                "defense_rank_modifier": -0.3,
                "total_offense_rank_modifier": 0.0,
                "weather_modifier": -0.2,
                "final_projection": 17.5,
            },
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        compare_players(
            db_session,
            CompareRequest(
                player_a_id="no-proj",
                player_b_id="has-proj",
                week=1,
                season=2026,
            ),
        )

    assert exc.value.status_code == 404
