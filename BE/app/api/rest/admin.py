from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.admin import AuditLog, FeatureFlag, ProviderKey
from app.models.avatar import Avatar, Persona
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from app.schemas.admin import (
    AuditLogOut,
    DashboardOut,
    FeatureFlagOut,
    FeatureFlagUpdate,
    ForceEndRequest,
    ProviderKeyOut,
    ProviderKeyUpsert,
)
from app.schemas.avatar import AvatarCreate, AvatarOut, AvatarUpdate
from app.services.session_service import end_session

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(
        UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT, UserRole.MODERATOR, UserRole.ANALYST
    ))],
)


async def _audit(db: DbSession, actor: User, action: str, resource: str, detail: str = "") -> None:
    db.add(
        AuditLog(
            actor_id=str(actor.id),
            action=action,
            resource=resource,
            detail=detail,
        )
    )


def _avatar_out(avatar: Avatar) -> AvatarOut:
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
        system_prompt_preview=persona.system_prompt[:160] if persona else None,
    )


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(db: DbSession) -> DashboardOut:
    active = (
        await db.execute(
            select(func.count()).select_from(Session).where(Session.status == SessionStatus.ACTIVE)
        )
    ).scalar_one()
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    duration = (
        await db.execute(select(func.coalesce(func.sum(Session.duration_sec), 0)))
    ).scalar_one()
    cost = (
        await db.execute(select(func.coalesce(func.sum(Session.cost_usd), 0.0)))
    ).scalar_one()
    return DashboardOut(
        active_sessions=int(active or 0),
        total_minutes_today=round(float(duration or 0) / 60.0, 2),
        total_users=int(users or 0),
        error_rate=0.0,
        latency_p50_ms=420,
        latency_p95_ms=780,
        cost_today_usd=round(float(cost or 0), 4),
    )


@router.get("/avatars", response_model=list[AvatarOut])
async def admin_list_avatars(db: DbSession) -> list[AvatarOut]:
    rows = (
        await db.execute(
            select(Avatar).options(selectinload(Avatar.personas)).order_by(Avatar.display_order)
        )
    ).scalars().all()
    return [_avatar_out(a) for a in rows]


@router.post(
    "/avatars",
    response_model=AvatarOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def admin_create_avatar(
    body: AvatarCreate, user: CurrentUser, db: DbSession
) -> AvatarOut:
    avatar = Avatar(
        name=body.name,
        description=body.description,
        category=body.category,
        thumbnail_url=body.thumbnail_url
        or f"https://api.dicebear.com/9.x/avataaars/svg?seed={body.name}",
        preview_video_url=body.preview_video_url,
        provider=body.provider,
        provider_avatar_id=body.provider_avatar_id or body.name.lower(),
        voice_id=body.voice_id,
        is_active=body.is_active,
        is_featured=body.is_featured,
        rollout_percent=body.rollout_percent,
    )
    db.add(avatar)
    await db.flush()
    db.add(
        Persona(
            avatar_id=avatar.id,
            system_prompt=body.system_prompt,
            greeting=body.greeting,
            is_published=True,
        )
    )
    await db.flush()
    await _audit(db, user, "avatar.create", str(avatar.id), body.name)
    avatar = (
        await db.execute(
            select(Avatar).options(selectinload(Avatar.personas)).where(Avatar.id == avatar.id)
        )
    ).scalar_one()
    return _avatar_out(avatar)


@router.patch(
    "/avatars/{avatar_id}",
    response_model=AvatarOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def admin_update_avatar(
    avatar_id: UUID, body: AvatarUpdate, user: CurrentUser, db: DbSession
) -> AvatarOut:
    avatar = (
        await db.execute(
            select(Avatar).options(selectinload(Avatar.personas)).where(Avatar.id == avatar_id)
        )
    ).scalar_one_or_none()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    data = body.model_dump(exclude_unset=True)
    prompt = data.pop("system_prompt", None)
    greeting = data.pop("greeting", None)
    for k, v in data.items():
        setattr(avatar, k, v)
    persona = next((p for p in avatar.personas if p.is_published), None)
    if persona:
        if prompt is not None:
            persona.system_prompt = prompt
            persona.version += 1
        if greeting is not None:
            persona.greeting = greeting
    await _audit(db, user, "avatar.update", str(avatar_id))
    return _avatar_out(avatar)


@router.get("/feature-flags", response_model=list[FeatureFlagOut])
async def list_flags(db: DbSession) -> list[FeatureFlagOut]:
    rows = (await db.execute(select(FeatureFlag))).scalars().all()
    return [FeatureFlagOut.model_validate(r) for r in rows]


@router.put(
    "/feature-flags/{key}",
    response_model=FeatureFlagOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def update_flag(
    key: str, body: FeatureFlagUpdate, user: CurrentUser, db: DbSession
) -> FeatureFlagOut:
    flag = (
        await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    ).scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    flag.value = body.value
    await _audit(db, user, "feature_flag.update", key, body.value)
    return FeatureFlagOut.model_validate(flag)


@router.get("/sessions/live")
async def live_sessions(db: DbSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Session).where(Session.status == SessionStatus.ACTIVE).limit(100)
        )
    ).scalars().all()
    return [
        {
            "id": str(s.id),
            "user_id": str(s.user_id),
            "avatar_id": str(s.avatar_id),
            "provider": s.provider,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        }
        for s in rows
    ]


@router.post(
    "/sessions/{session_id}/force-end",
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT))],
)
async def force_end(
    session_id: UUID, body: ForceEndRequest, user: CurrentUser, db: DbSession
) -> dict:
    await end_session(db, user, session_id, reason=body.reason, force=True)
    await _audit(db, user, "session.force_end", str(session_id), body.reason)
    return {"ok": True}


@router.get("/users")
async def list_users(db: DbSession) -> list[dict]:
    rows = (await db.execute(select(User).order_by(User.created_at.desc()).limit(200))).scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role.value,
            "quota_minutes": u.quota_minutes,
            "used_minutes": u.used_minutes,
            "is_active": u.is_active,
        }
        for u in rows
    ]


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def audit_logs(db: DbSession) -> list[AuditLogOut]:
    rows = (
        await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    ).scalars().all()
    return [AuditLogOut.model_validate(r) for r in rows]


@router.get("/providers", response_model=list[ProviderKeyOut])
async def list_providers(db: DbSession) -> list[ProviderKeyOut]:
    rows = (await db.execute(select(ProviderKey))).scalars().all()
    if not rows:
        return [
            ProviderKeyOut(provider="mock", is_active=True, priority=0, health="up", has_key=True),
            ProviderKeyOut(provider="heygen", is_active=False, priority=10, health="unconfigured", has_key=False),
            ProviderKeyOut(provider="anam", is_active=False, priority=20, health="unconfigured", has_key=False),
        ]
    return [
        ProviderKeyOut(
            provider=r.provider,
            is_active=r.is_active,
            priority=r.priority,
            health=r.health,
            has_key=bool(r.encrypted_key),
        )
        for r in rows
    ]


@router.put(
    "/providers",
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def upsert_provider(body: ProviderKeyUpsert, user: CurrentUser, db: DbSession) -> dict:
    # Store as opaque string for scaffold (use Fernet in production)
    row = (
        await db.execute(select(ProviderKey).where(ProviderKey.provider == body.provider))
    ).scalar_one_or_none()
    if not row:
        row = ProviderKey(provider=body.provider)
        db.add(row)
    row.encrypted_key = body.api_key  # TODO: encrypt with FERNET_KEY
    row.is_active = body.is_active
    row.priority = body.priority
    row.health = "configured"
    await _audit(db, user, "provider.upsert", body.provider)
    return {"ok": True, "provider": body.provider}
