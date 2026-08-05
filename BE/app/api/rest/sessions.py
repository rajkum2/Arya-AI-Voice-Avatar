from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.avatar import Avatar
from app.models.session import Conversation, Session, Transcript
from app.schemas.session import (
    ConversationOut,
    FeedbackRequest,
    SessionCreateRequest,
    SessionEndRequest,
    SessionOut,
    TranscriptLine,
    TranscriptOut,
)
from app.services.session_service import create_session, end_session

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionOut)
async def start_session(
    body: SessionCreateRequest, user: CurrentUser, db: DbSession
) -> SessionOut:
    settings = get_settings()
    session, p_session, greeting = await create_session(db, user, body)
    max_dur = settings.max_session_duration_sec
    if p_session.metadata.get("max_session_duration"):
        try:
            max_dur = int(p_session.metadata["max_session_duration"])
        except (TypeError, ValueError):
            pass
    return SessionOut(
        id=session.id,
        avatar_id=session.avatar_id,
        provider=session.provider,
        status=session.status,
        room_url=session.room_url,
        room_token=session.room_token,
        captions_enabled=session.captions_enabled,
        barge_in_enabled=session.barge_in_enabled,
        started_at=session.started_at,
        duration_sec=0,
        idle_timeout_sec=settings.session_idle_timeout_sec,
        max_duration_sec=max_dur,
        mock_mode=p_session.mock_mode,
        greeting=greeting,
        transport=str(p_session.metadata.get("transport") or ("mock" if p_session.mock_mode else "")),
        sandbox=bool(p_session.metadata.get("sandbox")),
        failover_reason=str(p_session.metadata.get("failover_reason") or ""),
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, user: CurrentUser, db: DbSession) -> SessionOut:
    settings = get_settings()
    session = (
        await db.execute(select(Session).where(Session.id == session_id))
    ).scalar_one_or_none()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut(
        id=session.id,
        avatar_id=session.avatar_id,
        provider=session.provider,
        status=session.status,
        room_url=session.room_url,
        room_token=session.room_token,
        captions_enabled=session.captions_enabled,
        barge_in_enabled=session.barge_in_enabled,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_sec=session.duration_sec,
        idle_timeout_sec=settings.session_idle_timeout_sec,
        max_duration_sec=settings.max_session_duration_sec,
        mock_mode=session.provider == "mock" or session.room_url.startswith("mock://"),
        greeting="",
    )


@router.delete("/sessions/{session_id}", response_model=SessionOut)
async def stop_session(
    session_id: UUID,
    user: CurrentUser,
    db: DbSession,
    body: SessionEndRequest | None = None,
) -> SessionOut:
    settings = get_settings()
    reason = body.reason if body else "user_ended"
    session = await end_session(db, user, session_id, reason=reason)
    return SessionOut(
        id=session.id,
        avatar_id=session.avatar_id,
        provider=session.provider,
        status=session.status,
        room_url=session.room_url,
        room_token=session.room_token,
        captions_enabled=session.captions_enabled,
        barge_in_enabled=session.barge_in_enabled,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_sec=session.duration_sec,
        idle_timeout_sec=settings.session_idle_timeout_sec,
        max_duration_sec=settings.max_session_duration_sec,
        mock_mode=session.provider == "mock",
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(user: CurrentUser, db: DbSession) -> list[ConversationOut]:
    rows = (
        await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    out: list[ConversationOut] = []
    for c in rows:
        session = (
            await db.execute(select(Session).where(Session.id == c.session_id))
        ).scalar_one_or_none()
        avatar = (
            await db.execute(select(Avatar).where(Avatar.id == c.avatar_id))
        ).scalar_one_or_none()
        out.append(
            ConversationOut(
                id=c.id,
                session_id=c.session_id,
                avatar_id=c.avatar_id,
                rating=c.rating,
                feedback=c.feedback,
                summary=c.summary,
                duration_sec=session.duration_sec if session else 0,
                created_at=c.created_at,
                avatar_name=avatar.name if avatar else None,
            )
        )
    return out


@router.get("/conversations/{conversation_id}/transcript", response_model=TranscriptOut)
async def get_transcript(
    conversation_id: UUID, user: CurrentUser, db: DbSession
) -> TranscriptOut:
    conv = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    lines = (
        await db.execute(
            select(Transcript)
            .where(Transcript.conversation_id == conversation_id)
            .order_by(Transcript.ts_ms, Transcript.created_at)
        )
    ).scalars().all()
    return TranscriptOut(
        conversation_id=conversation_id,
        lines=[
            TranscriptLine(
                speaker=t.speaker, text=t.text, is_final=t.is_final, ts_ms=t.ts_ms
            )
            for t in lines
        ],
    )


@router.post("/conversations/{conversation_id}/feedback")
async def feedback(
    conversation_id: UUID,
    body: FeedbackRequest,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    conv = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.rating = body.rating
    conv.feedback = body.feedback
    return {"ok": True}
