from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProviderSession:
    provider: str
    provider_session_id: str
    room_url: str = ""
    room_token: str = ""
    mock_mode: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class AvatarProvider(ABC):
    """Swappable avatar render / conversation provider (HeyGen, Anam, mock, in-house)."""

    name: str = "base"

    @abstractmethod
    async def create_session(
        self,
        *,
        avatar_provider_id: str,
        voice_id: str,
        system_prompt: str,
        greeting: str,
        user_id: str,
    ) -> ProviderSession:
        ...

    @abstractmethod
    async def send_text(self, session: ProviderSession, text: str) -> None:
        ...

    @abstractmethod
    async def interrupt(self, session: ProviderSession) -> None:
        ...

    @abstractmethod
    async def close_session(self, session: ProviderSession) -> None:
        ...

    async def keep_alive(self, session: ProviderSession) -> None:
        return None

    async def health(self) -> str:
        return "up"
