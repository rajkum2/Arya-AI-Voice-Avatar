from functools import lru_cache

from app.core.config import get_settings
from app.providers.anam import AnamAvatarProvider
from app.providers.base import AvatarProvider
from app.providers.heygen import HeyGenAvatarProvider
from app.providers.liveavatar import LiveAvatarProvider
from app.providers.mock import MockAvatarProvider


@lru_cache
def _providers() -> dict[str, AvatarProvider]:
    return {
        "mock": MockAvatarProvider(),
        "liveavatar": LiveAvatarProvider(),
        "heygen": HeyGenAvatarProvider(),  # legacy streaming (mostly retired)
        "anam": AnamAvatarProvider(),
    }


def get_avatar_provider(name: str | None = None) -> AvatarProvider:
    settings = get_settings()
    key = (name or settings.default_avatar_provider or "mock").lower()
    # Treat heygen default as liveavatar when LiveAvatar is configured (product rename)
    if key == "heygen" and (
        settings.liveavatar_api_key or settings.livekit_api_key
    ):
        key = "liveavatar"

    providers = _providers()
    if key not in providers:
        return providers["mock"]

    if key == "liveavatar":
        if not (settings.liveavatar_api_key or settings.livekit_api_key):
            return providers["mock"]
        return providers["liveavatar"]

    if key == "heygen" and not settings.heygen_api_key:
        return providers["mock"]

    return providers[key]


def list_providers() -> list[str]:
    return list(_providers().keys())
