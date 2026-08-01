from fastapi import APIRouter
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.admin import FeatureFlag
from app.models.user import ConsentRecord
from app.schemas.session import BootstrapOut

router = APIRouter(tags=["bootstrap"])

AI_DISCLOSURE = (
    "You will be talking to an AI avatar, not a human. "
    "Your voice may be processed to generate responses. "
    "This notice is provided under EU AI Act Article 50 transparency obligations."
)


def _flag_bool(flags: dict, key: str, default: bool) -> bool:
    raw = flags.get(key)
    if raw is None:
        return default
    return str(raw).lower() in ("1", "true", "yes", "on")


@router.get("/bootstrap", response_model=BootstrapOut)
async def bootstrap(db: DbSession) -> BootstrapOut:
    settings = get_settings()
    flags = {
        f.key: f.value
        for f in (await db.execute(select(FeatureFlag))).scalars().all()
    }
    return BootstrapOut(
        maintenance_mode=_flag_bool(flags, "maintenance_mode", settings.maintenance_mode),
        captions_default=_flag_bool(flags, "captions_default", settings.captions_default),
        barge_in_enabled=_flag_bool(flags, "barge_in_enabled", settings.barge_in_enabled),
        min_android_version=settings.min_android_version,
        min_web_version=settings.min_web_version,
        consent_version=settings.consent_version,
        consent_required=True,
        ai_disclosure=AI_DISCLOSURE,
        features={
            "history": True,
            "export_data": True,
            "delete_account": True,
            "mock_conversation": True,
        },
    )


@router.get("/bootstrap/me", response_model=BootstrapOut)
async def bootstrap_me(user: CurrentUser, db: DbSession) -> BootstrapOut:
    settings = get_settings()
    flags = {
        f.key: f.value
        for f in (await db.execute(select(FeatureFlag))).scalars().all()
    }
    consent = (
        await db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user.id)
            .order_by(ConsentRecord.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    consent_required = not (
        consent
        and consent.understand_ai
        and consent.voice_processing
        and consent.consent_version == settings.consent_version
    )
    return BootstrapOut(
        maintenance_mode=_flag_bool(flags, "maintenance_mode", settings.maintenance_mode),
        captions_default=_flag_bool(flags, "captions_default", settings.captions_default),
        barge_in_enabled=_flag_bool(flags, "barge_in_enabled", settings.barge_in_enabled),
        min_android_version=settings.min_android_version,
        min_web_version=settings.min_web_version,
        consent_version=settings.consent_version,
        consent_required=consent_required,
        ai_disclosure=AI_DISCLOSURE,
        features={
            "history": True,
            "export_data": True,
            "delete_account": True,
            "mock_conversation": True,
        },
    )
