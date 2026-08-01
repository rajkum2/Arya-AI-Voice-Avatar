from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AvatarOut(BaseModel):
    id: UUID
    name: str
    description: str
    category: str
    thumbnail_url: str
    preview_video_url: str
    provider: str
    voice_id: str
    is_active: bool
    is_featured: bool
    rollout_percent: int
    greeting: Optional[str] = None
    system_prompt_preview: Optional[str] = None

    model_config = {"from_attributes": True}


class AvatarCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "general"
    thumbnail_url: str = ""
    preview_video_url: str = ""
    provider: str = "mock"
    provider_avatar_id: str = ""
    voice_id: str = ""
    is_active: bool = True
    is_featured: bool = False
    rollout_percent: int = Field(default=100, ge=0, le=100)
    system_prompt: str = "You are a helpful AI avatar assistant."
    greeting: str = "Hello! How can I help you today?"


class AvatarUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    rollout_percent: Optional[int] = Field(default=None, ge=0, le=100)
    voice_id: Optional[str] = None
    system_prompt: Optional[str] = None
    greeting: Optional[str] = None
