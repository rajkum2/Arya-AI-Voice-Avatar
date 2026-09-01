import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Call(Base):
    """Phone-call channel record (Ringg / mock). Separate from avatar Sessions."""

    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    avatar_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("avatars.id"), index=True, nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    provider_call_id: Mapped[str] = mapped_column(String(256), default="", index=True)
    callee_name: Mapped[str] = mapped_column(String(120), default="")
    to_number: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(32), default="registered")
    custom_args: Mapped[dict] = mapped_column(JSON, default=dict)
    transcript: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    recording_url: Mapped[str] = mapped_column(String(512), default="")
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    processed_events: Mapped[list] = mapped_column(JSON, default=list)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
