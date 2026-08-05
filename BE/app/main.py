import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.rest import admin, auth, avatars, bootstrap, privacy, sessions
from app.api.ws.session_ws import router as ws_router
from app.core.config import get_settings
from app.core.database import Base, engine, AsyncSessionLocal
from app.services.seed import seed_if_empty

logger = logging.getLogger("arya")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create tables (Alembic recommended for prod; create_all for scaffold)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as db:
            await seed_if_empty(db)
        logger.info("Arya API ready (v%s) — DB connected", __version__)
    except Exception:
        # Stay up for /health so ops can see the service; DB routes will fail until fixed
        logger.exception(
            "Database init/seed failed — API is up but data routes will error"
        )
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Arya AI Voice Avatar API",
        version=__version__,
        description="Provider-agnostic real-time AI avatar backend",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = FastAPI()  # unused — keep routes on main

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(bootstrap.router, prefix="/api/v1")
    app.include_router(avatars.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(privacy.router, prefix="/api/v1")
    app.include_router(ws_router)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": __version__,
            "provider_default": settings.default_avatar_provider,
            "maintenance": settings.maintenance_mode,
        }

    @app.get("/")
    async def root():
        return {
            "name": "Arya AI Voice Avatar API",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
