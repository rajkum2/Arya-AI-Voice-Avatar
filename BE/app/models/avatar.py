import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Avatar(Base):
    __tablename__ = "avatars"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="general")
    thumbnail_url: Mapped[str] = mapped_column(String(512), default="")
    preview_video_url: Mapped[str] = mapped_column(String(512), default="")
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    provider_avatar_id: Mapped[str] = mapped_column(String(128), default="")
    voice_id: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, default=100)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    personas: Mapped[list["Persona"]] = relationship(back_populates="avatar")


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    avatar_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("avatars.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="default")
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful AI avatar assistant.")
    greeting: Mapped[str] = mapped_column(Text, default="Hello! How can I help you today?")
    llm_model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    avatar: Mapped["Avatar"] = relationship(back_populates="personas")
