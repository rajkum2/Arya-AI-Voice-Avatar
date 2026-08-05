from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


def _engine_url_and_args() -> tuple[str, dict]:
    url = settings.database_url
    connect_args: dict = {}

    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return url, connect_args

    if url.startswith("postgresql+asyncpg://") or url.startswith("postgresql://"):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        sslmode = q.pop("sslmode", None)
        # asyncpg does not accept sslmode as a libpq query arg
        clean = urlunparse(parsed._replace(query="&".join(f"{k}={v}" for k, v in q.items()) if q else ""))
        if "asyncpg" not in clean:
            clean = clean.replace("postgresql://", "postgresql+asyncpg://", 1)

        needs_ssl = (
            sslmode in ("require", "verify-ca", "verify-full", "prefer")
            or "supabase.com" in host
            or "supabase.co" in host
            or settings.environment == "production"
        )
        if needs_ssl and not url.startswith("sqlite"):
            # True enables TLS without custom cert verification (Supabase default)
            connect_args["ssl"] = True
        return clean, connect_args

    return url, connect_args


_db_url, _connect_args = _engine_url_and_args()

engine = create_async_engine(
    _db_url,
    echo=settings.environment == "development" and settings.database_url.startswith("sqlite"),
    connect_args=_connect_args,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
