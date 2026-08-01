from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.session import SessionStatus


class SessionCreateRequest(BaseModel):
    avatar_id: UUID
    captions_enabled: Optional[bool] = None
    barge_in_enabled: Optional[bool] = None


class SessionOut(BaseModel):
    id: UUID
    avatar_id: UUID
    provider: str
    status: SessionStatus
    room_url: str
    room_token: str
    captions_enabled: bool
    barge_in_enabled: bool
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_sec: int = 0
    idle_timeout_sec: int = 120
    max_duration_sec: int = 1200
    # Mock mode helper: simulated turn channel instructions
    mock_mode: bool = False
    greeting: str = ""

    model_config = {"from_attributes": True}


class SessionEndRequest(BaseModel):
    reason: str = "user_ended"


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: str = ""


class ConversationOut(BaseModel):
    id: UUID
    session_id: UUID
    avatar_id: UUID
    rating: Optional[int] = None
    feedback: str = ""
    summary: str = ""
    duration_sec: int = 0
    created_at: datetime
    avatar_name: Optional[str] = None

    model_config = {"from_attributes": True}


class TranscriptLine(BaseModel):
    speaker: str
    text: str
    is_final: bool
    ts_ms: int


class TranscriptOut(BaseModel):
    conversation_id: UUID
    lines: list[TranscriptLine]


class BootstrapOut(BaseModel):
    maintenance_mode: bool
    captions_default: bool
    barge_in_enabled: bool
    min_android_version: int
    min_web_version: int
    consent_version: str
    consent_required: bool
    ai_disclosure: str
    features: dict
