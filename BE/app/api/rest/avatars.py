from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession
from app.models.avatar import Avatar
from app.schemas.avatar import AvatarOut

router = APIRouter(prefix="/avatars", tags=["avatars"])


def _to_out(avatar: Avatar) -> AvatarOut:
    persona = next((p for p in avatar.personas if p.is_published), None)
    return AvatarOut(
        id=avatar.id,
        name=avatar.name,
        description=avatar.description,
        category=avatar.category,
        thumbnail_url=avatar.thumbnail_url,
        preview_video_url=avatar.preview_video_url,
        provider=avatar.provider,
        voice_id=avatar.voice_id,
        is_active=avatar.is_active,
        is_featured=avatar.is_featured,
        rollout_percent=avatar.rollout_percent,
        greeting=persona.greeting if persona else None,
        system_prompt_preview=(persona.system_prompt[:160] + "…")
        if persona and len(persona.system_prompt) > 160
        else (persona.system_prompt if persona else None),
    )


@router.get("", response_model=list[AvatarOut])
async def list_avatars(
    db: DbSession,
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[AvatarOut]:
    stmt = (
        select(Avatar)
        .options(selectinload(Avatar.personas))
        .where(Avatar.is_active.is_(True))
        .order_by(Avatar.display_order, Avatar.name)
    )
    if category:
        stmt = stmt.where(Avatar.category == category)
    rows = (await db.execute(stmt)).scalars().all()
    if q:
        ql = q.lower()
        rows = [a for a in rows if ql in a.name.lower() or ql in a.description.lower()]
    return [_to_out(a) for a in rows if a.rollout_percent > 0]


@router.get("/{avatar_id}", response_model=AvatarOut)
async def get_avatar(avatar_id: UUID, db: DbSession) -> AvatarOut:
    avatar = (
        await db.execute(
            select(Avatar)
            .options(selectinload(Avatar.personas))
            .where(Avatar.id == avatar_id)
        )
    ).scalar_one_or_none()
    if not avatar or not avatar.is_active:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return _to_out(avatar)
