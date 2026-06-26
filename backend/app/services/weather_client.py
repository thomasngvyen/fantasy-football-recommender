from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db.tables import Matchup, Weather

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
STADIUMS_PATH = FIXTURES_DIR / "stadiums.json"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
RAIN_WEATHER_TYPES = frozenset({"Rain", "Drizzle", "Thunderstorm"})
MAX_KICKOFF_DELTA = timedelta(hours=2, minutes=30)


@dataclass(frozen=True)
class WeatherSnapshot:
    """Normalized weather at kickoff, mapped to our Weather table columns."""

    wind_mph: float
    temp_f: float | None
    precip_mm: float
    is_rain: bool


@dataclass
class WeatherClient:
    """Thin wrapper around OpenWeather's 5-day / 3-hour forecast API."""

    api_key: str
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> WeatherClient | None:
        api_key = settings.openweather_api_key
        if not api_key:
            return None
        return cls(api_key=api_key)

    def fetch_forecast(self, lat: float, lon: float) -> list[dict[str, Any]]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                FORECAST_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial",
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload.get("list", [])

    def forecast_at(
        self, lat: float, lon: float, kickoff: datetime
    ) -> WeatherSnapshot | None:
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        else:
            kickoff = kickoff.astimezone(timezone.utc)

        slots = self.fetch_forecast(lat, lon)
        if not slots:
            return None

        best_slot = min(
            slots,
            key=lambda slot: abs(
                datetime.fromtimestamp(slot["dt"], tz=timezone.utc) - kickoff
            ),
        )
        slot_time = datetime.fromtimestamp(best_slot["dt"], tz=timezone.utc)
        if abs(slot_time - kickoff) > MAX_KICKOFF_DELTA:
            return None

        return parse_forecast_slot(best_slot)


def parse_forecast_slot(slot: dict[str, Any]) -> WeatherSnapshot:
    wind_mph = float(slot.get("wind", {}).get("speed", 0.0))
    temp_f = slot.get("main", {}).get("temp")
    temp_f = float(temp_f) if temp_f is not None else None
    precip_mm = float(slot.get("rain", {}).get("3h", 0.0))
    weather_main = slot.get("weather", [{}])[0].get("main", "")
    pop = float(slot.get("pop", 0.0))
    is_rain = (
        weather_main in RAIN_WEATHER_TYPES or precip_mm > 0.0 or pop >= 0.5
    )
    return WeatherSnapshot(
        wind_mph=round(wind_mph, 2),
        temp_f=round(temp_f, 2) if temp_f is not None else None,
        precip_mm=round(precip_mm, 2),
        is_rain=is_rain,
    )


def load_stadium_coords() -> dict[str, tuple[float, float]]:
    stadiums = json.loads(STADIUMS_PATH.read_text(encoding="utf-8"))
    return {
        row["team"]: (float(row["latitude"]), float(row["longitude"]))
        for row in stadiums
    }


def home_team_for_matchup(matchup: Matchup) -> str | None:
    if matchup.player is None or matchup.player.team is None:
        return None
    if matchup.opponent is None:
        return None
    return matchup.player.team if matchup.is_home else matchup.opponent


def upsert_weather(
    session: Session, matchup_id: int, snapshot: WeatherSnapshot
) -> Weather:
    existing = session.execute(
        select(Weather).where(Weather.matchup_id == matchup_id)
    ).scalar_one_or_none()

    if existing is None:
        weather = Weather(
            matchup_id=matchup_id,
            wind_mph=snapshot.wind_mph,
            temp_f=snapshot.temp_f,
            precip_mm=snapshot.precip_mm,
            is_rain=snapshot.is_rain,
        )
        session.add(weather)
        return weather

    existing.wind_mph = snapshot.wind_mph
    existing.temp_f = snapshot.temp_f
    existing.precip_mm = snapshot.precip_mm
    existing.is_rain = snapshot.is_rain
    return existing


def sync_weather_for_week(
    session: Session,
    week: int,
    season: int,
    client: WeatherClient,
) -> dict[str, Any]:
    """
    Fetch outdoor-game forecasts once per unique kickoff and upsert Weather rows.

    Dome games are skipped (projection.py already neutralizes weather when is_dome).
    """
    coords = load_stadium_coords()
    matchups = session.scalars(
        select(Matchup)
        .where(Matchup.week == week, Matchup.season == season)
        .options(selectinload(Matchup.player))
    ).all()

    games: dict[tuple[str, datetime], list[Matchup]] = defaultdict(list)
    skipped_dome = 0
    skipped_no_home = 0

    for matchup in matchups:
        if matchup.is_dome:
            skipped_dome += 1
            continue

        home_team = home_team_for_matchup(matchup)
        if home_team is None or home_team not in coords:
            skipped_no_home += 1
            continue

        games[(home_team, matchup.game_datetime)].append(matchup)

    games_fetched = 0
    forecast_unavailable = 0
    rows_created = 0
    rows_updated = 0
    errors: list[str] = []

    for (home_team, kickoff), game_matchups in games.items():
        lat, lon = coords[home_team]
        try:
            snapshot = client.forecast_at(lat, lon, kickoff)
        except httpx.HTTPError as exc:
            errors.append(f"{home_team} @ {kickoff.isoformat()}: {exc}")
            continue

        if snapshot is None:
            forecast_unavailable += 1
            continue

        games_fetched += 1
        for matchup in game_matchups:
            existing = session.execute(
                select(Weather).where(Weather.matchup_id == matchup.id)
            ).scalar_one_or_none()
            upsert_weather(session, matchup.id, snapshot)
            if existing is None:
                rows_created += 1
            else:
                rows_updated += 1

    return {
        "status": "success",
        "week": week,
        "season": season,
        "outdoor_games": len(games),
        "games_fetched": games_fetched,
        "forecast_unavailable": forecast_unavailable,
        "rows_created": rows_created,
        "rows_updated": rows_updated,
        "skipped_dome": skipped_dome,
        "skipped_no_home": skipped_no_home,
        "errors": errors,
    }
