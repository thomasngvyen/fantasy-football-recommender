from app.config import load_settings, settings


def test_default_settings():
    assert settings.database_url == "sqlite:///./fantasy.db"
    assert settings.data_mode in {"live", "mock"}
    assert settings.is_live or settings.is_mock


def test_load_settings_returns_settings_instance():
    loaded = load_settings()
    assert loaded.database_url == settings.database_url
