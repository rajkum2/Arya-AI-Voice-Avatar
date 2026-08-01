from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import create_token, hash_password, safe_decode, verify_password
from app.models.user import ConsentRecord, User
from app.schemas.auth import (
    ConsentOut,
    ConsentRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_verified=user.is_verified,
        quota_minutes=user.quota_minutes,
        used_minutes=user.used_minutes,
        remaining_minutes=max(0, user.quota_minutes - user.used_minutes),
    )


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    exists = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    settings = get_settings()
    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        display_name=body.display_name or body.email.split("@")[0],
        quota_minutes=settings.default_quota_minutes,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return TokenResponse(
        access_token=create_token(str(user.id), token_type="access"),
        refresh_token=create_token(str(user.id), token_type="refresh"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account suspended")
    return TokenResponse(
        access_token=create_token(str(user.id), token_type="access"),
        refresh_token=create_token(str(user.id), token_type="refresh"),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    payload = safe_decode(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    sub = payload.get("sub")
    return TokenResponse(
        access_token=create_token(str(sub), token_type="access"),
        refresh_token=create_token(str(sub), token_type="refresh"),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return _user_out(user)


@router.post("/consent", response_model=ConsentOut)
async def submit_consent(
    body: ConsentRequest, user: CurrentUser, db: DbSession
) -> ConsentOut:
    if not body.understand_ai or not body.voice_processing:
        raise HTTPException(
            status_code=400,
            detail="understand_ai and voice_processing consents are required",
        )
    settings = get_settings()
    record = ConsentRecord(
        user_id=user.id,
        consent_version=settings.consent_version,
        understand_ai=body.understand_ai,
        voice_processing=body.voice_processing,
        store_transcripts=body.store_transcripts,
        improve_service=body.improve_service,
    )
    db.add(record)
    await db.flush()
    return ConsentOut(
        consent_version=record.consent_version,
        understand_ai=record.understand_ai,
        voice_processing=record.voice_processing,
        store_transcripts=record.store_transcripts,
        improve_service=record.improve_service,
        created_at=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/consent", response_model=ConsentOut | None)
async def get_consent(user: CurrentUser, db: DbSession) -> ConsentOut | None:
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user.id)
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None
    return ConsentOut(
        consent_version=record.consent_version,
        understand_ai=record.understand_ai,
        voice_processing=record.voice_processing,
        store_transcripts=record.store_transcripts,
        improve_service=record.improve_service,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )
