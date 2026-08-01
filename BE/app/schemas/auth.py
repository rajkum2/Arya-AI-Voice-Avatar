from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    role: UserRole
    is_verified: bool
    quota_minutes: int
    used_minutes: int
    remaining_minutes: int

    model_config = {"from_attributes": True}


class ConsentRequest(BaseModel):
    understand_ai: bool
    voice_processing: bool
    store_transcripts: bool = False
    improve_service: bool = False


class ConsentOut(BaseModel):
    consent_version: str
    understand_ai: bool
    voice_processing: bool
    store_transcripts: bool
    improve_service: bool
    created_at: Optional[str] = None
