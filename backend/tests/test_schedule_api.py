from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_schedule_weeks(client: TestClient):
    response = client.get("/schedule/weeks", params={"start": 1, "end": 3})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["week"] == 1
    assert data[0]["teams_playing"] == 32
    assert data[0]["teams_on_bye"] == []


def test_get_schedule_week_bye(client: TestClient):
    response = client.get("/schedule/weeks/11")
    assert response.status_code == 200
    data = response.json()
    assert data["teams_playing"] == 26
    assert len(data["teams_on_bye"]) == 6


def test_get_schedule_week_missing(client: TestClient):
    response = client.get("/schedule/weeks/99")
    assert response.status_code == 404
