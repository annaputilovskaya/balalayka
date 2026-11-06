from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "dev"
    log_level: str = "INFO"
    database_url: str
    redis_url: str
    secret_key: SecretStr
    public_base_url: str = "http://localhost"
    session_cookie_secure: bool = True
    templates_dir: Path = FRONTEND_DIR / "templates"
    static_dir: Path = FRONTEND_DIR / "static"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
