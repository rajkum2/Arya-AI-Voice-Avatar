from functools import lru_cache

from app.core.config import get_settings
from app.providers.anam import AnamAvatarProvider
from app.providers.base import AvatarProvider
from app.providers.heygen import HeyGenAvatarProvider
from app.providers.mock import MockAvatarProvider


@lru_cache
def _providers() -> dict[str, AvatarProvider]:
    return {
        "mock": MockAvatarProvider(),
        "heygen": HeyGenAvatarProvider(),
        "anam": AnamAvatarProvider(),
    }


def get_avatar_provider(name: str | None = None) -> AvatarProvider:
    settings = get_settings()
    key = (name or settings.default_avatar_provider or "mock").lower()
    providers = _providers()
    if key not in providers:
        return providers["mock"]
    provider = providers[key]
    # Auto-fallback if HeyGen selected but unconfigured
    if key == "heygen" and not settings.heygen_api_key:
        return providers["mock"]
    return provider


def list_providers() -> list[str]:
    return list(_providers().keys())
