import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.weather_client import (
    WeatherClient,
    parse_forecast_slot,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "openweather_forecast_sample.json"


def test_parse_forecast_slot_rain():
    slots = json.loads(FIXTURE_PATH.read_text())["list"]
    snapshot = parse_forecast_slot(slots[1])
    assert snapshot.wind_mph == 18.2
    assert snapshot.temp_f == 68.0
    assert snapshot.precip_mm == 2.5
    assert snapshot.is_rain is True


def test_parse_forecast_slot_clear():
    slots = json.loads(FIXTURE_PATH.read_text())["list"]
    snapshot = parse_forecast_slot(slots[0])
    assert snapshot.is_rain is False


def test_forecast_at_picks_closest_slot(monkeypatch):
    slots = json.loads(FIXTURE_PATH.read_text())["list"]
    client = WeatherClient(api_key="test-key")

    monkeypatch.setattr(client, "fetch_forecast", lambda lat, lon: slots)

    kickoff = datetime.fromtimestamp(1757552400, tz=timezone.utc)
    snapshot = client.forecast_at(42.0, -78.0, kickoff)

    assert snapshot is not None
    assert snapshot.wind_mph == 18.2
    assert snapshot.is_rain is True


def test_forecast_at_returns_none_when_kickoff_outside_window(monkeypatch):
    slots = json.loads(FIXTURE_PATH.read_text())["list"]
    client = WeatherClient(api_key="test-key")
    monkeypatch.setattr(client, "fetch_forecast", lambda lat, lon: slots)

    kickoff = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert client.forecast_at(42.0, -78.0, kickoff) is None
