from functools import lru_cache

from app.core.config import get_settings
from app.providers.bolti import BoltiCallProvider
from app.providers.call_base import CallProvider
from app.providers.call_mock import MockCallProvider
from app.providers.ringg import RinggCallProvider


@lru_cache
def _call_providers() -> dict[str, CallProvider]:
    return {
        "mock": MockCallProvider(),
        "ringg": RinggCallProvider(),
        "bolti": BoltiCallProvider(),
    }


def _configured(name: str) -> bool:
    settings = get_settings()
    if name == "ringg":
        return bool(
            settings.ringg_api_key
            and settings.ringg_agent_id
            and settings.ringg_from_number_id
        )
    if name == "bolti":
        return bool(
            settings.bolti_token
            and settings.bolti_agent_id
            and settings.bolti_from_number
        )
    return False


def get_call_provider(name: str | None = None) -> CallProvider:
    """Resolve a call provider; unconfigured/unknown names fall back to mock
    (same fallback philosophy as the avatar provider registry)."""
    providers = _call_providers()
    key = (name or "").lower()
    if key in ("ringg", "bolti"):
        return providers[key] if _configured(key) else providers["mock"]
    # Auto/default: prefer Ringg, then Bolti, then mock
    for candidate in ("ringg", "bolti"):
        if _configured(candidate):
            return providers[candidate]
    return providers["mock"]


def list_call_providers() -> list[str]:
    return list(_call_providers().keys())
