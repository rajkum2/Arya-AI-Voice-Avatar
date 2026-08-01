import uuid
from typing import Any

from app.providers.base import AvatarProvider, ProviderSession


class MockAvatarProvider(AvatarProvider):
    """Local mock for development without third-party keys."""

    name = "mock"

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    async def create_session(
        self,
        *,
        avatar_provider_id: str,
        voice_id: str,
        system_prompt: str,
        greeting: str,
        user_id: str,
    ) -> ProviderSession:
        sid = f"mock_{uuid.uuid4().hex[:12]}"
        self._sessions[sid] = {
            "avatar_provider_id": avatar_provider_id,
            "voice_id": voice_id,
            "system_prompt": system_prompt,
            "greeting": greeting,
            "user_id": user_id,
            "history": [],
        }
        return ProviderSession(
            provider=self.name,
            provider_session_id=sid,
            room_url=f"mock://room/{sid}",
            room_token=f"mock-token-{sid}",
            mock_mode=True,
            metadata={"greeting": greeting},
        )

    async def send_text(self, session: ProviderSession, text: str) -> None:
        store = self._sessions.get(session.provider_session_id)
        if store is not None:
            store["history"].append({"role": "user", "text": text})

    async def interrupt(self, session: ProviderSession) -> None:
        return None

    async def close_session(self, session: ProviderSession) -> None:
        self._sessions.pop(session.provider_session_id, None)

    def mock_reply(self, session_id: str, user_text: str) -> str:
        store = self._sessions.get(session_id, {})
        name = store.get("avatar_provider_id") or "Arya"
        return (
            f"[{name}] I heard you say: “{user_text.strip()}”. "
            "This is a mock avatar response while you wire HeyGen/Anam."
        )
