from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.admin import FeatureFlag
from app.models.avatar import Avatar, Persona
from app.models.user import User, UserRole


async def seed_if_empty(db: AsyncSession) -> None:
    settings = get_settings()

    # Feature flags
    existing_flags = (await db.execute(select(FeatureFlag))).scalars().all()
    if not existing_flags:
        db.add_all(
            [
                FeatureFlag(
                    key="captions_default",
                    value=str(settings.captions_default).lower(),
                    description="Default captions on/off for new sessions",
                ),
                FeatureFlag(
                    key="barge_in_enabled",
                    value=str(settings.barge_in_enabled).lower(),
                    description="Allow user to interrupt avatar speech",
                ),
                FeatureFlag(
                    key="maintenance_mode",
                    value=str(settings.maintenance_mode).lower(),
                    description="Block new sessions when true",
                ),
            ]
        )

    # Admin user
    admin = (
        await db.execute(select(User).where(User.email == "admin@example.com"))
    ).scalar_one_or_none()
    if not admin:
        db.add(
            User(
                email="admin@example.com",
                hashed_password=hash_password("admin12345"),
                display_name="Arya Admin",
                role=UserRole.SUPER_ADMIN,
                is_verified=True,
                quota_minutes=10_000,
            )
        )

    demo = (
        await db.execute(select(User).where(User.email == "demo@example.com"))
    ).scalar_one_or_none()
    if not demo:
        db.add(
            User(
                email="demo@example.com",
                hashed_password=hash_password("demo12345"),
                display_name="Demo User",
                role=UserRole.USER,
                is_verified=True,
                quota_minutes=settings.default_quota_minutes,
            )
        )

    avatars = (await db.execute(select(Avatar))).scalars().all()
    # LiveAvatar sandbox Wayne UUID (production: replace with public/user avatar UUID)
    liveavatar_default_id = "dd73ea75-1218-4ef3-92ce-606d5f7fbc0a"
    use_liveavatar = bool(
        settings.liveavatar_api_key
        or settings.livekit_api_key
        or settings.default_avatar_provider in ("liveavatar", "heygen")
    )

    if not avatars:
        seeds = [
            (
                "Maya",
                "Patient language tutor who keeps conversations light and encouraging.",
                "tutor",
                "You are Maya, a patient language tutor. Speak clearly, correct gently, keep answers short for voice.",
                "Hi! I'm Maya, your language partner. What would you like to practice today?",
            ),
            (
                "Arjun",
                "Calm productivity coach focused on small next steps.",
                "coach",
                "You are Arjun, a calm productivity coach. Be concise, actionable, and supportive.",
                "Hello, I'm Arjun. What's the one thing you want to make progress on?",
            ),
            (
                "Nova",
                "Friendly product-support specialist for the Arya platform.",
                "support",
                "You are Nova, Arya support. Explain features clearly and escalate complex issues politely.",
                "Hi, I'm Nova from Arya support. How can I help?",
            ),
        ]
        for i, (name, desc, cat, prompt, greet) in enumerate(seeds):
            avatar = Avatar(
                name=name,
                description=desc,
                category=cat,
                thumbnail_url=f"https://api.dicebear.com/9.x/avataaars/svg?seed={name}",
                provider="liveavatar" if use_liveavatar else "mock",
                provider_avatar_id=liveavatar_default_id if use_liveavatar else name.lower(),
                voice_id="default",
                is_active=True,
                is_featured=i == 0,
                rollout_percent=100,
                display_order=i,
            )
            db.add(avatar)
            await db.flush()
            db.add(
                Persona(
                    avatar_id=avatar.id,
                    name="default",
                    system_prompt=prompt,
                    greeting=greet,
                    is_published=True,
                )
            )
    elif use_liveavatar:
        # Upgrade existing mock avatars to LiveAvatar sandbox IDs
        for avatar in avatars:
            if avatar.provider == "mock" or not avatar.provider_avatar_id or len(
                str(avatar.provider_avatar_id)
            ) < 32:
                avatar.provider = "liveavatar"
                avatar.provider_avatar_id = liveavatar_default_id

    await db.commit()
