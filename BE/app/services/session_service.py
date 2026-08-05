from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.avatar import Avatar, Persona
from app.models.session import Conversation, Session, SessionStatus, Transcript
from app.models.user import ConsentRecord, User
from app.providers.base import ProviderSession
from app.providers.registry import get_avatar_provider
from app.schemas.session import SessionCreateRequest


async def _latest_consent(db: AsyncSession, user_id: UUID) -> ConsentRecord | None:
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_session(
    db: AsyncSession,
    user: User,
    body: SessionCreateRequest,
) -> tuple[Session, ProviderSession, str]:
    settings = get_settings()
    if settings.maintenance_mode:
        raise HTTPException(status_code=503, detail="Maintenance mode")

    consent = await _latest_consent(db, user.id)
    if not consent or not consent.understand_ai or not consent.voice_processing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required AI disclosure and voice-processing consent missing",
        )

    remaining = user.quota_minutes - user.used_minutes
    if remaining <= 0:
        raise HTTPException(status_code=402, detail="Quota exceeded")

    result = await db.execute(
        select(Avatar)
        .options(selectinload(Avatar.personas))
        .where(Avatar.id == body.avatar_id, Avatar.is_active.is_(True))
    )
    avatar = result.scalar_one_or_none()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")

    persona = next((p for p in avatar.personas if p.is_published), None)
    greeting = persona.greeting if persona else "Hello!"
    system_prompt = persona.system_prompt if persona else "You are a helpful AI."

    # Prefer global default when avatar still marked mock but LiveAvatar/HeyGen is configured
    provider_name = avatar.provider
    if provider_name == "mock" and settings.default_avatar_provider not in (
        "",
        "mock",
    ):
        provider_name = settings.default_avatar_provider

    provider = get_avatar_provider(provider_name)
    try:
        p_session = await provider.create_session(
            avatar_provider_id=avatar.provider_avatar_id or avatar.name,
            voice_id=avatar.voice_id,
            system_prompt=system_prompt,
            greeting=greeting,
            user_id=str(user.id),
        )
    except Exception as exc:  # noqa: BLE001
        # Fail over to mock so local demos keep working
        if provider_name != "mock":
            provider = get_avatar_provider("mock")
            p_session = await provider.create_session(
                avatar_provider_id=avatar.provider_avatar_id or avatar.name,
                voice_id=avatar.voice_id,
                system_prompt=system_prompt,
                greeting=greeting,
                user_id=str(user.id),
            )
            p_session.metadata["failover_reason"] = str(exc)
        else:
            raise HTTPException(status_code=502, detail=f"Provider error: {exc}") from exc

    captions = (
        body.captions_enabled
        if body.captions_enabled is not None
        else settings.captions_default
    )
    barge = (
        body.barge_in_enabled
        if body.barge_in_enabled is not None
        else settings.barge_in_enabled
    )

    session = Session(
        user_id=user.id,
        avatar_id=avatar.id,
        provider=p_session.provider,
        provider_session_id=p_session.provider_session_id,
        room_url=p_session.room_url,
        room_token=p_session.room_token,
        status=SessionStatus.ACTIVE,
        captions_enabled=captions,
        barge_in_enabled=barge,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()

    conversation = Conversation(
        session_id=session.id,
        user_id=user.id,
        avatar_id=avatar.id,
        summary="",
    )
    db.add(conversation)
    await db.flush()

    # Store greeting as first avatar line if transcripts consented
    if consent.store_transcripts and greeting:
        db.add(
            Transcript(
                conversation_id=conversation.id,
                speaker="avatar",
                text=greeting,
                is_final=True,
                ts_ms=0,
            )
        )

    return session, p_session, greeting


async def end_session(
    db: AsyncSession,
    user: User,
    session_id: UUID,
    reason: str = "user_ended",
    force: bool = False,
) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not force and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.status in (SessionStatus.ENDED, SessionStatus.FORCE_ENDED):
        return session

    now = datetime.now(timezone.utc)
    started = session.started_at or session.created_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    duration = max(0, int((now - started).total_seconds()))
    session.ended_at = now
    session.duration_sec = duration
    session.end_reason = reason
    session.status = SessionStatus.FORCE_ENDED if force else SessionStatus.ENDED
    # Rough cost estimate for mock / managed
    session.cost_usd = round((duration / 60.0) * 0.10, 4)

    # Quota accounting (round up minutes)
    minutes = max(1, (duration + 59) // 60) if duration > 0 else 0
    if minutes:
        owner = user if session.user_id == user.id else None
        if owner is None:
            r = await db.execute(select(User).where(User.id == session.user_id))
            owner = r.scalar_one_or_none()
        if owner:
            owner.used_minutes = min(owner.quota_minutes, owner.used_minutes + minutes)

    provider = get_avatar_provider(session.provider)
    try:
        await provider.close_session(
            ProviderSession(
                provider=session.provider,
                provider_session_id=session.provider_session_id,
                room_url=session.room_url,
                room_token=session.room_token,
            )
        )
    except Exception:  # noqa: BLE001
        pass

    return session
