from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.db.tables import Base, Matchup, Player, Projection
from app.main import app
from app.services.sleeper_client import SleeperClient
from test_compare import _seed_compare_fixtures


def _mock_sleeper_roster(monkeypatch: pytest.MonkeyPatch) -> None:
    roster = {
        "qb-a": {
            "team": "KC",
            "status": "Active",
            "active": True,
            "depth_chart_order": 1,
            "depth_chart_position": "QB",
            "fantasy_positions": ["QB"],
            "player_id": "qb-a",
            "first_name": "Alpha",
            "last_name": "QB",
        },
        "qb-b": {
            "team": "BUF",
            "status": "Active",
            "active": True,
            "depth_chart_order": 2,
            "depth_chart_position": "QB",
            "fantasy_positions": ["QB"],
            "player_id": "qb-b",
            "first_name": "Beta",
            "last_name": "QB",
        },
        "qb-1": {
            "team": "KC",
            "status": "Active",
            "active": True,
            "depth_chart_order": 1,
            "depth_chart_position": "QB",
            "fantasy_positions": ["QB"],
            "player_id": "qb-1",
            "first_name": "Some",
            "last_name": "QB",
        },
        "rb-1": {
            "team": "KC",
            "status": "Active",
            "active": True,
            "depth_chart_order": 1,
            "depth_chart_position": "RB",
            "fantasy_positions": ["RB"],
            "player_id": "rb-1",
            "first_name": "Some",
            "last_name": "RB",
        },
        "no-proj": {
            "team": "KC",
            "status": "Active",
            "active": True,
            "depth_chart_order": 1,
            "depth_chart_position": "QB",
            "fantasy_positions": ["QB"],
            "player_id": "no-proj",
            "first_name": "No",
            "last_name": "Proj",
        },
        "has-proj": {
            "team": "BUF",
            "status": "Active",
            "active": True,
            "depth_chart_order": 2,
            "depth_chart_position": "QB",
            "fantasy_positions": ["QB"],
            "player_id": "has-proj",
            "first_name": "Has",
            "last_name": "Proj",
        },
    }

    def fake_get_active_players(self, *, position=None, refresh=False):
        from app.services.sleeper_client import SleeperClient as SC

        records = []
        for player_id in ("qb-a", "qb-b"):
            player = roster[player_id]
            record = SC.to_player_record(self, player)
            if record is None:
                continue
            if position and record["position"] != position.upper():
                continue
            records.append(record)
        return records

    def fake_get_player_record(self, player_id: str, *, refresh=False):
        from app.services.sleeper_client import SleeperClient as SC

        player = roster.get(player_id)
        if player is None:
            return None
        return SC.to_player_record(self, player)

    monkeypatch.setattr(SleeperClient, "get_active_players", fake_get_active_players)
    monkeypatch.setattr(SleeperClient, "get_player_record", fake_get_player_record)


@pytest.fixture(autouse=True)
def mock_sleeper_players(monkeypatch: pytest.MonkeyPatch):
    _mock_sleeper_roster(monkeypatch)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client: TestClient, db_session: Session) -> TestClient:
    _seed_compare_fixtures(db_session)
    return client


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_get_players(seeded_client: TestClient):
    response = seeded_client.get("/players")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {player["sleeper_id"] for player in data} == {"qb-a", "qb-b"}


def test_get_players_filter_by_position(seeded_client: TestClient):
    response = seeded_client.get("/players", params={"position": "QB"})
    assert response.status_code == 200
    assert len(response.json()) == 2

    empty = seeded_client.get("/players", params={"position": "TE"})
    assert empty.status_code == 200
    assert empty.json() == []


def test_post_compare(seeded_client: TestClient):
    response = seeded_client.post(
        "/compare",
        json={
            "player_a_id": "qb-a",
            "player_b_id": "qb-b",
            "week": 1,
            "season": 2026,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["winner"]["sleeper_id"] == "qb-a"
    assert data["loser"]["sleeper_id"] == "qb-b"
    assert data["margin_of_victory"] == 4.0
    assert data["winner"]["breakdown"]["final_projection"] == 21.5
    assert "Start Alpha QB over Beta QB" in data["recommendation"]


def test_post_compare_rejects_same_player(client: TestClient):
    response = client.post(
        "/compare",
        json={
            "player_a_id": "qb-a",
            "player_b_id": "qb-a",
            "week": 1,
            "season": 2026,
        },
    )
    assert response.status_code == 422


def test_post_compare_rejects_position_mismatch(db_session: Session, client: TestClient):
    db_session.add_all(
        [
            Player(
                sleeper_id="qb-1",
                name="Some QB",
                position="QB",
                team="KC",
                base_projection=20.0,
            ),
            Player(
                sleeper_id="rb-1",
                name="Some RB",
                position="RB",
                team="KC",
                base_projection=12.0,
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/compare",
        json={
            "player_a_id": "qb-1",
            "player_b_id": "rb-1",
            "week": 1,
            "season": 2026,
        },
    )
    assert response.status_code == 400


def test_post_compare_missing_player(seeded_client: TestClient):
    response = seeded_client.post(
        "/compare",
        json={
            "player_a_id": "qb-a",
            "player_b_id": "missing-id",
            "week": 1,
            "season": 2026,
        },
    )
    assert response.status_code == 404


def test_post_compare_missing_projection(db_session: Session, client: TestClient):
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

    response = client.post(
        "/compare",
        json={
            "player_a_id": "no-proj",
            "player_b_id": "has-proj",
            "week": 1,
            "season": 2026,
        },
    )
    assert response.status_code == 404


def test_post_compare_rejects_non_rosterable_player(
    seeded_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def fake_get_player_record(self, player_id: str, *, refresh=False):
        if player_id == "qb-b":
            return None
        from app.services.sleeper_client import SleeperClient as SC

        player = {
            "team": "KC",
            "status": "Active",
            "active": True,
            "depth_chart_order": 1,
            "depth_chart_position": "QB",
            "fantasy_positions": ["QB"],
            "player_id": player_id,
            "first_name": "Alpha",
            "last_name": "QB",
        }
        return SC.to_player_record(self, player)

    monkeypatch.setattr(SleeperClient, "get_player_record", fake_get_player_record)

    response = seeded_client.post(
        "/compare",
        json={
            "player_a_id": "qb-a",
            "player_b_id": "qb-b",
            "week": 1,
            "season": 2026,
        },
    )
    assert response.status_code == 400
    assert "not currently rosterable" in response.json()["detail"]
