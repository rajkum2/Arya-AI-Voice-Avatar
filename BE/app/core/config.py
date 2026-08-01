from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    secret_key: str = "dev-secret-change-me-in-production-32chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    database_url: str = "sqlite+aiosqlite:///./arya.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    heygen_api_key: str = ""
    anam_api_key: str = ""
    tavus_api_key: str = ""
    deepgram_api_key: str = ""
    openai_api_key: str = ""
    elevenlabs_api_key: str = ""

    default_avatar_provider: str = "mock"
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    fernet_key: str = ""

    captions_default: bool = True
    barge_in_enabled: bool = True
    maintenance_mode: bool = False
    min_android_version: int = 1
    min_web_version: int = 1

    consent_version: str = "2026-08-01"
    default_quota_minutes: int = 60
    session_idle_timeout_sec: int = 120
    max_session_duration_sec: int = 1200

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
