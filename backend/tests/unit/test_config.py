import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert "database_url" in str(error.value)


def test_session_cookie_secure_false_is_parsed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    settings = Settings(_env_file=None)
    assert settings.session_cookie_secure is False
    assert "test-secret" not in repr(settings)
