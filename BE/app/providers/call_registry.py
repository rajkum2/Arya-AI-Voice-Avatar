from functools import lru_cache

from app.core.config import get_settings
from app.providers.call_base import CallProvider
from app.providers.call_mock import MockCallProvider
from app.providers.ringg import RinggCallProvider


@lru_cache
def _call_providers() -> dict[str, CallProvider]:
    return {
        "mock": MockCallProvider(),
        "ringg": RinggCallProvider(),
    }


def get_call_provider(name: str | None = None) -> CallProvider:
    """Ringg when fully configured, mock otherwise (same fallback as avatars)."""
    settings = get_settings()
    key = (name or "ringg").lower()
    providers = _call_providers()
    if key == "ringg":
        configured = bool(
            settings.ringg_api_key
            and settings.ringg_agent_id
            and settings.ringg_from_number_id
        )
        if not configured:
            return providers["mock"]
        return providers["ringg"]
    return providers.get(key, providers["mock"])


def list_call_providers() -> list[str]:
    return list(_call_providers().keys())
