"""WebSocket channel for mock turn-taking, captions, and control events."""

from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import safe_decode
from app.models.session import Conversation, Session, SessionStatus, Transcript
from app.providers.mock import MockAvatarProvider
from app.providers.registry import get_avatar_provider

router = APIRouter()


async def _auth_user_id(token: str | None) -> str | None:
    if not token:
        return None
    payload = safe_decode(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


@router.websocket("/ws/session/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    token = websocket.query_params.get("token")
    user_id = await _auth_user_id(token)
    if not user_id:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close(code=4401)
        return

    try:
        sid = UUID(session_id)
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Invalid session id"})
        await websocket.close(code=4400)
        return

    async with AsyncSessionLocal() as db:
        session = (
            await db.execute(select(Session).where(Session.id == sid))
        ).scalar_one_or_none()
        if not session or str(session.user_id) != user_id:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close(code=4404)
            return
        if session.status != SessionStatus.ACTIVE:
            await websocket.send_json({"type": "error", "message": "Session not active"})
            await websocket.close(code=4409)
            return

        conv = (
            await db.execute(
                select(Conversation).where(Conversation.session_id == sid).limit(1)
            )
        ).scalar_one_or_none()

        await websocket.send_json(
            {
                "type": "state",
                "state": "listening",
                "captions_enabled": session.captions_enabled,
                "barge_in_enabled": session.barge_in_enabled,
                "provider": session.provider,
                "mock_mode": session.provider == "mock"
                or session.room_url.startswith("mock://"),
            }
        )

        # Send greeting as speaking state
        if session.provider == "mock" or session.room_url.startswith("mock://"):
            greeting_line = None
            if conv:
                t = (
                    await db.execute(
                        select(Transcript)
                        .where(Transcript.conversation_id == conv.id)
                        .order_by(Transcript.ts_ms)
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if t and t.speaker == "avatar":
                    greeting_line = t.text
            if greeting_line:
                await websocket.send_json({"type": "state", "state": "speaking"})
                await websocket.send_json(
                    {
                        "type": "transcript",
                        "speaker": "avatar",
                        "text": greeting_line,
                        "is_final": True,
                        "ts_ms": 0,
                    }
                )
                await asyncio.sleep(0.4)
                await websocket.send_json({"type": "state", "state": "listening"})

        start = time.time()
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                    continue

                mtype = msg.get("type")
                if mtype == "ping":
                    await websocket.send_json({"type": "pong", "ts": time.time()})
                    continue

                if mtype == "interrupt":
                    if session.barge_in_enabled:
                        provider = get_avatar_provider(session.provider)
                        # best-effort
                        try:
                            from app.providers.base import ProviderSession

                            await provider.interrupt(
                                ProviderSession(
                                    provider=session.provider,
                                    provider_session_id=session.provider_session_id,
                                    room_url=session.room_url,
                                    room_token=session.room_token,
                                )
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        await websocket.send_json({"type": "state", "state": "listening"})
                        await websocket.send_json({"type": "interrupted"})
                    continue

                if mtype == "user_text" or mtype == "final_transcript":
                    text = (msg.get("text") or "").strip()
                    if not text:
                        continue
                    ts_ms = int((time.time() - start) * 1000)
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "speaker": "user",
                            "text": text,
                            "is_final": True,
                            "ts_ms": ts_ms,
                        }
                    )
                    if conv:
                        db.add(
                            Transcript(
                                conversation_id=conv.id,
                                speaker="user",
                                text=text,
                                is_final=True,
                                ts_ms=ts_ms,
                            )
                        )
                        await db.commit()

                    await websocket.send_json({"type": "state", "state": "thinking"})
                    await asyncio.sleep(0.35)

                    provider = get_avatar_provider(session.provider)
                    reply: str
                    if isinstance(provider, MockAvatarProvider) or session.provider == "mock":
                        mock = provider if isinstance(provider, MockAvatarProvider) else MockAvatarProvider()
                        reply = mock.mock_reply(session.provider_session_id, text)
                    else:
                        reply = f"Thanks for saying: {text}"

                    await websocket.send_json({"type": "state", "state": "speaking"})
                    # stream-ish captions
                    words = reply.split()
                    partial = ""
                    for w in words:
                        partial = (partial + " " + w).strip()
                        await websocket.send_json(
                            {
                                "type": "transcript",
                                "speaker": "avatar",
                                "text": partial,
                                "is_final": False,
                                "ts_ms": int((time.time() - start) * 1000),
                            }
                        )
                        await asyncio.sleep(0.05)

                    final_ts = int((time.time() - start) * 1000)
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "speaker": "avatar",
                            "text": reply,
                            "is_final": True,
                            "ts_ms": final_ts,
                        }
                    )
                    if conv:
                        db.add(
                            Transcript(
                                conversation_id=conv.id,
                                speaker="avatar",
                                text=reply,
                                is_final=True,
                                ts_ms=final_ts,
                            )
                        )
                        await db.commit()
                    await websocket.send_json({"type": "state", "state": "listening"})
                    continue

                if mtype == "end":
                    await websocket.send_json({"type": "ended"})
                    break

                await websocket.send_json(
                    {"type": "error", "message": f"Unknown type: {mtype}"}
                )
        except WebSocketDisconnect:
            return
