from functools import lru_cache
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Normalize Postgres URLs for SQLAlchemy async + Supabase.

    Accepts common provider forms:
      - postgres://...
      - postgresql://...
      - postgresql+asyncpg://...
      - postgresql+psycopg2://...
    and rewrites to postgresql+asyncpg://...
    Ensures sslmode=require for Supabase hosts when missing.
    """
    if not url:
        return url
    raw = url.strip().strip('"').strip("'")

    # Railway / Heroku sometimes use postgres://
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    # Drop sync drivers; async engine needs asyncpg
    for prefix in (
        "postgresql+psycopg2://",
        "postgresql+psycopg://",
        "postgresql+psycopg2cffi://",
    ):
        if raw.startswith(prefix):
            raw = "postgresql+asyncpg://" + raw[len(prefix) :]
            break
    else:
        if raw.startswith("postgresql://"):
            raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    # Supabase requires SSL; asyncpg uses 'ssl' query param (or connect_args)
    try:
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        is_supabase = "supabase.com" in host or "supabase.co" in host
        if is_supabase or "pooler.supabase" in host:
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            # asyncpg ignores sslmode; we keep it for tooling and handle SSL in database.py
            if "sslmode" not in q:
                q["sslmode"] = "require"
            raw = urlunparse(parsed._replace(query=urlencode(q)))
    except Exception:
        pass

    return raw


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

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db(cls, v: object) -> object:
        if isinstance(v, str):
            return normalize_database_url(v)
        return v

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
