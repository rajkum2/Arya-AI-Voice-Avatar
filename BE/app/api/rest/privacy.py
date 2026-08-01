import json
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.session import Conversation, Session, Transcript
from app.models.user import ConsentRecord, User

router = APIRouter(prefix="/me", tags=["privacy"])


@router.get("/export")
async def export_data(user: CurrentUser, db: DbSession) -> dict:
    """GDPR Art. 20 — portable export of profile + transcripts."""
    consents = (
        await db.execute(select(ConsentRecord).where(ConsentRecord.user_id == user.id))
    ).scalars().all()
    conversations = (
        await db.execute(select(Conversation).where(Conversation.user_id == user.id))
    ).scalars().all()
    sessions = (
        await db.execute(select(Session).where(Session.user_id == user.id))
    ).scalars().all()
    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "quota_minutes": user.quota_minutes,
            "used_minutes": user.used_minutes,
        },
        "consents": [
            {
                "version": c.consent_version,
                "understand_ai": c.understand_ai,
                "voice_processing": c.voice_processing,
                "store_transcripts": c.store_transcripts,
                "improve_service": c.improve_service,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consents
        ],
        "sessions": [
            {
                "id": str(s.id),
                "avatar_id": str(s.avatar_id),
                "duration_sec": s.duration_sec,
                "status": s.status.value,
            }
            for s in sessions
        ],
        "conversations": [],
    }
    for conv in conversations:
        lines = (
            await db.execute(
                select(Transcript).where(Transcript.conversation_id == conv.id)
            )
        ).scalars().all()
        export["conversations"].append(
            {
                "id": str(conv.id),
                "session_id": str(conv.session_id),
                "rating": conv.rating,
                "transcript": [{"speaker": t.speaker, "text": t.text} for t in lines],
            }
        )
    return export


@router.delete("/account")
async def delete_account(user: CurrentUser, db: DbSession) -> dict:
    """GDPR Art. 17 — right to erasure (soft-delete + scrub for scaffold)."""
    user.email = f"deleted_{user.id}@erased.local"
    user.display_name = "Deleted User"
    user.is_active = False
    user.hashed_password = "!"
    # Remove transcripts
    conversations = (
        await db.execute(select(Conversation).where(Conversation.user_id == user.id))
    ).scalars().all()
    for conv in conversations:
        lines = (
            await db.execute(select(Transcript).where(Transcript.conversation_id == conv.id))
        ).scalars().all()
        for line in lines:
            await db.delete(line)
        conv.feedback = ""
        conv.summary = ""
    return {"ok": True, "message": "Account scheduled for erasure"}
