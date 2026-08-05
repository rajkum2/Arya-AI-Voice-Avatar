"""HeyGen LiveAvatar provider (FULL mode, LiveKit transport).

API: https://api.liveavatar.com
Auth: X-API-KEY header
Flow: POST /v1/sessions/token → POST /v1/sessions/start → client joins LiveKit
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.base import AvatarProvider, ProviderSession

logger = logging.getLogger(__name__)

LIVEAVATAR_BASE = "https://api.liveavatar.com"

# Sandbox-only avatar (Wayne) — free, ~1 min sessions
SANDBOX_AVATAR_ID = "dd73ea75-1218-4ef3-92ce-606d5f7fbc0a"


class LiveAvatarProvider(AvatarProvider):
    name = "liveavatar"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        # Prefer dedicated key; many setups store LiveAvatar key as LIVEKIT_API_KEY by mistake
        self.api_key = (
            api_key
            or settings.liveavatar_api_key
            or settings.livekit_api_key
            or ""
        )
        self.sandbox = settings.liveavatar_sandbox
        self._sessions: dict[str, dict[str, Any]] = {}

    def _api_headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
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
            raise RuntimeError(
                "LIVEAVATAR_API_KEY not configured "
                "(get a key from https://app.liveavatar.com/developers)"
            )

        # Sandbox forces Wayne avatar
        avatar_id = SANDBOX_AVATAR_ID if self.sandbox else (
            avatar_provider_id or SANDBOX_AVATAR_ID
        )
        # UUID-shaped only — mock names like "maya" are invalid
        if len(avatar_id) < 32 or " " in avatar_id:
            if self.sandbox:
                avatar_id = SANDBOX_AVATAR_ID
            else:
                raise RuntimeError(
                    f"LiveAvatar requires a UUID avatar_id, got: {avatar_provider_id!r}"
                )

        settings = get_settings()
        persona: dict[str, Any] = {"language": "en"}

        # Prefer env voice, then avatar DB voice if UUID-shaped
        resolved_voice = (settings.liveavatar_voice_id or voice_id or "").strip()
        if resolved_voice and len(resolved_voice) >= 32:
            persona["voice_id"] = resolved_voice

        # REQUIRED for conversation — without context LiveAvatar stays in restricted mode
        resolved_context = (settings.liveavatar_context_id or "").strip()
        if resolved_context:
            persona["context_id"] = resolved_context
        else:
            logger.warning(
                "LIVEAVATAR_CONTEXT_ID is empty — avatar will not respond to speech "
                "(restricted mode)"
            )

        token_body: dict[str, Any] = {
            "mode": "FULL",
            "avatar_id": avatar_id,
            "is_sandbox": self.sandbox,
            "avatar_persona": persona,
            "interactivity_type": "CONVERSATIONAL",
            "video_settings": {"quality": "medium", "encoding": "H264"},
            "max_session_duration": min(
                settings.max_session_duration_sec,
                60 if self.sandbox else settings.max_session_duration_sec,
            ),
        }
        logger.info(
            "LiveAvatar token persona context=%s voice=%s sandbox=%s avatar=%s",
            persona.get("context_id"),
            persona.get("voice_id"),
            self.sandbox,
            avatar_id,
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            token_resp = await client.post(
                f"{LIVEAVATAR_BASE}/v1/sessions/token",
                headers=self._api_headers(),
                json=token_body,
            )
            if token_resp.status_code >= 400:
                logger.error("LiveAvatar token failed: %s", token_resp.text)
                raise RuntimeError(
                    f"LiveAvatar token failed ({token_resp.status_code}): "
                    f"{token_resp.text[:300]}"
                )

            token_data = token_resp.json().get("data") or {}
            session_id = token_data.get("session_id") or ""
            session_token = token_data.get("session_token") or ""
            if not session_id or not session_token:
                raise RuntimeError(f"LiveAvatar token response missing fields: {token_data}")

            start_resp = await client.post(
                f"{LIVEAVATAR_BASE}/v1/sessions/start",
                headers={
                    "Authorization": f"Bearer {session_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if start_resp.status_code >= 400:
                logger.error("LiveAvatar start failed: %s", start_resp.text)
                raise RuntimeError(
                    f"LiveAvatar start failed ({start_resp.status_code}): "
                    f"{start_resp.text[:300]}"
                )

            start_data = start_resp.json().get("data") or {}
            room_url = start_data.get("livekit_url") or ""
            room_token = start_data.get("livekit_client_token") or ""
            max_dur = start_data.get("max_session_duration")

        self._sessions[session_id] = {
            "session_token": session_token,
            "user_id": user_id,
            "system_prompt": system_prompt,
            "greeting": greeting,
            "sandbox": self.sandbox,
        }

        return ProviderSession(
            provider=self.name,
            provider_session_id=session_id,
            room_url=room_url,
            room_token=room_token,
            mock_mode=False,
            metadata={
                "greeting": greeting,
                "session_token": session_token,
                "sandbox": self.sandbox,
                "avatar_id": avatar_id,
                "max_session_duration": max_dur,
                "transport": "livekit",
            },
        )

    async def send_text(self, session: ProviderSession, text: str) -> None:
        # FULL mode handles speech via LiveKit room agent; text path is FE WS mock fallback
        return None

    async def interrupt(self, session: ProviderSession) -> None:
        return None

    async def close_session(self, session: ProviderSession) -> None:
        store = self._sessions.pop(session.provider_session_id, {})
        token = store.get("session_token") or session.metadata.get("session_token")
        if not self.api_key:
            return
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Prefer session bearer; also send API key as fallback
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-API-KEY": self.api_key,
                }
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                await client.post(
                    f"{LIVEAVATAR_BASE}/v1/sessions/stop",
                    headers=headers,
                    json={
                        "session_id": session.provider_session_id,
                        "reason": "USER_CLOSED",
                    },
                )
        except Exception:  # noqa: BLE001
            logger.exception("LiveAvatar stop_session failed")

    async def health(self) -> str:
        if not self.api_key:
            return "unconfigured"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"{LIVEAVATAR_BASE}/v1/users/credits",
                    headers=self._api_headers(),
                )
                return "up" if r.status_code == 200 else f"degraded:{r.status_code}"
        except Exception:  # noqa: BLE001
            return "down"
