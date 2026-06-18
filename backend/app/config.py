from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


@dataclass(frozen=True)
class Settings:
    """
    Application configuration loaded once from environment variables.

    Import `settings` anywhere instead of calling os.getenv directly.
    """

    data_mode: str
    database_url: str
    openweather_api_key: str | None
    cors_origins: tuple[str, ...]

    @property
    def is_mock(self) -> bool:
        return self.data_mode == "mock"

    @property
    def is_live(self) -> bool:
        return self.data_mode == "live"

    @property
    def openweather_enabled(self) -> bool:
        return bool(self.openweather_api_key)


def load_settings() -> Settings:
    data_mode = (_env("DATA_MODE", "live") or "live").lower()
    if data_mode not in {"live", "mock"}:
        raise ValueError("DATA_MODE must be 'live' or 'mock'")

    cors_raw = _env("CORS_ORIGINS", "http://localhost:5173") or ""
    cors_origins = tuple(
        origin.strip() for origin in cors_raw.split(",") if origin.strip()
    )

    return Settings(
        data_mode=data_mode,
        database_url=_env("DATABASE_URL", "sqlite:///./fantasy.db")
        or "sqlite:///./fantasy.db",
        openweather_api_key=_env("OPENWEATHER_API_KEY"),
        cors_origins=cors_origins,
    )


settings = load_settings()
