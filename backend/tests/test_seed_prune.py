from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.seed import prune_players_not_on_roster, seed_players
from app.db.tables import Base, Matchup, Player, Projection
from app.services.sleeper_client import SleeperClient


def test_prune_players_deletes_related_matchups_and_projections(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    kept = Player(
        sleeper_id="kept",
        name="Kept Player",
        position="QB",
        team="KC",
        base_projection=20.0,
    )
    removed = Player(
        sleeper_id="removed",
        name="Removed Player",
        position="QB",
        team="BUF",
        base_projection=10.0,
    )
    session.add_all([kept, removed])
    session.flush()

    matchup = Matchup(
        player_id=removed.id,
        week=1,
        season=2026,
        opponent="MIA",
        is_home=True,
        is_dome=False,
        game_datetime=datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
    )
    session.add(matchup)
    session.flush()
    session.add(
        Projection(
            player_id=removed.id,
            matchup_id=matchup.id,
            week=1,
            season=2026,
            adjusted_points=12.0,
            breakdown_json={"final_projection": 12.0},
        )
    )
    session.commit()

    removed_count = prune_players_not_on_roster(session, {"kept"})
    session.commit()

    assert removed_count == 1
    assert session.scalar(select(func.count()).select_from(Player)) == 1
    assert session.scalar(select(func.count()).select_from(Matchup)) == 0
    assert session.scalar(select(func.count()).select_from(Projection)) == 0


def test_seed_players_prunes_inactive_by_default(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    session.add(
        Player(
            sleeper_id="old-fa",
            name="Old Free Agent",
            position="WR",
            team=None,
            base_projection=0.0,
        )
    )
    session.commit()

    roster = {
        "active-1": {
            "player_id": "active-1",
            "first_name": "Active",
            "last_name": "Player",
            "team": "KC",
            "status": "Active",
            "active": True,
            "fantasy_positions": ["QB"],
            "depth_chart_order": 1,
            "depth_chart_position": "QB",
        }
    }

    monkeypatch.setattr(
        SleeperClient,
        "get_all_players",
        lambda self, *, refresh=False: roster,
    )
    monkeypatch.setattr(
        "app.db.seed.fetch_season_averages",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        "app.db.seed.resolve_base_projection",
        lambda **kwargs: 15.0,
    )

    count = seed_players(session, SleeperClient(), stats_season=None)
    session.commit()

    assert count == 1
    remaining = session.scalars(select(Player)).all()
    assert len(remaining) == 1
    assert remaining[0].sleeper_id == "active-1"
