"""HeyGen LiveAvatar provider (server-side token mint).

Requires HEYGEN_API_KEY. Until configured, create_session raises RuntimeError
so the registry can fall back to mock.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.base import AvatarProvider, ProviderSession

logger = logging.getLogger(__name__)

HEYGEN_BASE = "https://api.heygen.com"


class HeyGenAvatarProvider(AvatarProvider):
    name = "heygen"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.heygen_api_key
        self._sessions: dict[str, dict[str, Any]] = {}

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_session(
        self,
        *,
        avatar_provider_id: str,
        voice_id: str,
        system_prompt: str,
        greeting: str,
        user_id: str,
    ) -> ProviderSession:
        if not self.api_key:
            raise RuntimeError("HEYGEN_API_KEY not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Streaming avatar session create — endpoint shapes evolve; keep isolated.
            # Flow (conceptual): create_token → new session → start → task
            token_resp = await client.post(
                f"{HEYGEN_BASE}/v1/streaming.create_token",
                headers=self._headers(),
            )
            if token_resp.status_code >= 400:
                logger.error("HeyGen create_token failed: %s", token_resp.text)
                raise RuntimeError(f"HeyGen create_token failed: {token_resp.status_code}")

            token_data = token_resp.json()
            access_token = (
                token_data.get("data", {}).get("token")
                or token_data.get("token")
                or ""
            )

            new_resp = await client.post(
                f"{HEYGEN_BASE}/v1/streaming.new",
                headers={**self._headers(), "Authorization": f"Bearer {access_token}"},
                json={
                    "quality": "medium",
                    "avatar_name": avatar_provider_id or "default",
                    "voice": {"voice_id": voice_id} if voice_id else None,
                    "version": "v2",
                    "video_encoding": "H264",
                    "activity_idle_timeout": get_settings().session_idle_timeout_sec,
                },
            )
            if new_resp.status_code >= 400:
                logger.error("HeyGen streaming.new failed: %s", new_resp.text)
                raise RuntimeError(f"HeyGen streaming.new failed: {new_resp.status_code}")

            data = new_resp.json().get("data", new_resp.json())
            session_id = data.get("session_id") or data.get("sessionId") or ""
            room_url = data.get("url") or data.get("livekit_url") or ""
            room_token = data.get("access_token") or data.get("token") or access_token

        self._sessions[session_id] = {
            "access_token": access_token,
            "system_prompt": system_prompt,
            "greeting": greeting,
            "user_id": user_id,
        }
        return ProviderSession(
            provider=self.name,
            provider_session_id=session_id,
            room_url=room_url,
            room_token=room_token,
            mock_mode=False,
            metadata={"greeting": greeting},
        )

    async def send_text(self, session: ProviderSession, text: str) -> None:
        if not self.api_key:
            return
        store = self._sessions.get(session.provider_session_id, {})
        token = store.get("access_token") or session.room_token
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{HEYGEN_BASE}/v1/streaming.task",
                headers={**self._headers(), "Authorization": f"Bearer {token}"},
                json={
                    "session_id": session.provider_session_id,
                    "text": text,
                    "task_type": "talk",
                },
            )

    async def interrupt(self, session: ProviderSession) -> None:
        if not self.api_key:
            return
        store = self._sessions.get(session.provider_session_id, {})
        token = store.get("access_token") or session.room_token
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{HEYGEN_BASE}/v1/streaming.interrupt",
                headers={**self._headers(), "Authorization": f"Bearer {token}"},
                json={"session_id": session.provider_session_id},
            )

    async def close_session(self, session: ProviderSession) -> None:
        if not self.api_key:
            return
        store = self._sessions.get(session.provider_session_id, {})
        token = store.get("access_token") or session.room_token
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(
                    f"{HEYGEN_BASE}/v1/streaming.stop",
                    headers={**self._headers(), "Authorization": f"Bearer {token}"},
                    json={"session_id": session.provider_session_id},
                )
        finally:
            self._sessions.pop(session.provider_session_id, None)

    async def health(self) -> str:
        return "up" if self.api_key else "unconfigured"
