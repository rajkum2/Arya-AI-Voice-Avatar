"""Anam provider stub — plug CARA / LiveKit session when ANAM_API_KEY is set."""

from app.core.config import get_settings
from app.providers.base import AvatarProvider, ProviderSession
from app.providers.mock import MockAvatarProvider


class AnamAvatarProvider(AvatarProvider):
    name = "anam"

    def __init__(self) -> None:
        self.api_key = get_settings().anam_api_key
        self._fallback = MockAvatarProvider()

    async def create_session(self, **kwargs) -> ProviderSession:
        if not self.api_key:
            session = await self._fallback.create_session(**kwargs)
            session.provider = self.name
            session.metadata["note"] = "Anam key missing; using mock transport"
            return session
        # TODO: Implement Anam session create against official API.
        session = await self._fallback.create_session(**kwargs)
        session.provider = self.name
        session.mock_mode = True
        session.metadata["note"] = "Anam integration scaffold — wire LiveKit plugin next"
        return session

    async def send_text(self, session: ProviderSession, text: str) -> None:
        await self._fallback.send_text(session, text)

    async def interrupt(self, session: ProviderSession) -> None:
        await self._fallback.interrupt(session)

    async def close_session(self, session: ProviderSession) -> None:
        await self._fallback.close_session(session)

    async def health(self) -> str:
        return "up" if self.api_key else "unconfigured"
