from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

E164_PATTERN = r"^\+[1-9]\d{6,14}$"


class CallCreateRequest(BaseModel):
    avatar_id: Optional[UUID] = None
    callee_name: str = Field(min_length=1, max_length=120)
    to_number: str = Field(pattern=E164_PATTERN)
    custom_args: dict[str, str] = {}


class CallOut(BaseModel):
    id: UUID
    avatar_id: Optional[UUID] = None
    provider: str
    status: str
    callee_name: str
    to_number: str
    duration_sec: int = 0
    transcript: str = ""
    summary: str = ""
    recording_url: str = ""
    analysis: dict = {}
    mock_mode: bool = False
    created_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
