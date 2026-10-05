from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[4] / ".env", extra="ignore")
    app_name: str = "HomeMate"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://homate:homate_local@127.0.0.1:5432/homate"
    jwt_secret: str = Field(default="homate-development-change-this-secret-before-production", min_length=32)
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7
    jwt_cookie_name: str = "homate_refresh"
    ws_heartbeat_seconds: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    weather_api_key: str = ""
    weather_lat: float = 21.028
    weather_lon: float = 105.804
    weather_ttl_seconds: int = 600
    occupancy_vacant_minutes: int = 30
    occupancy_cooldown_minutes: int = 30
    occupancy_watchdog_interval_seconds: int = 15
    energy_sampler_interval_seconds: int = 60

    @model_validator(mode="after")
    def require_production_secret(self):
        if self.app_env == "production" and self.jwt_secret.startswith("homate-development-"):
            raise ValueError("Set a private JWT_SECRET for production")
        if not self.database_url.startswith("postgresql"):
            raise ValueError("DATABASE_URL must point to PostgreSQL")
        return self


@lru_cache
def get_settings():
    return Settings()
