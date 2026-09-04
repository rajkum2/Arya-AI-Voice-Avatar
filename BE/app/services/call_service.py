import asyncio
import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.avatar import Avatar
from app.models.call import Call
from app.models.user import User
from app.providers.call_base import CallResult
from app.providers.call_registry import get_call_provider
from app.schemas.call import CallCreateRequest
from app.services.session_service import _latest_consent

logger = logging.getLogger("arya")

MOCK_AUTOCOMPLETE_DELAY_SEC = 8

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "error"}


async def create_call(
    db: AsyncSession,
    user: User,
    body: CallCreateRequest,
    callback_base_url: str,
) -> tuple[Call, CallResult]:
    settings = get_settings()
    if settings.maintenance_mode:
        raise HTTPException(status_code=503, detail="Maintenance mode")

    consent = await _latest_consent(db, user.id)
    if not consent or not consent.understand_ai or not consent.voice_processing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required AI disclosure and voice-processing consent missing",
        )

    remaining = user.quota_minutes - user.used_minutes
    if remaining <= 0:
        raise HTTPException(status_code=402, detail="Quota exceeded")

    avatar = None
    if body.avatar_id is not None:
        result = await db.execute(
            select(Avatar)
            .options(selectinload(Avatar.personas))
            .where(Avatar.id == body.avatar_id, Avatar.is_active.is_(True))
        )
        avatar = result.scalar_one_or_none()
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")

    custom_args = dict(body.custom_args)
    custom_args.setdefault("callee_name", body.callee_name)

    callback_url = f"{callback_base_url.rstrip('/')}/api/v1/webhooks/ringg"
    provider = get_call_provider(body.provider)
    try:
        result = await provider.start_call(
            callee_name=body.callee_name,
            to_number=body.to_number,
            agent_id=settings.ringg_agent_id,
            from_number_id=settings.ringg_from_number_id,
            custom_args=custom_args,
            callback_url=callback_url,
        )
    except Exception as exc:  # noqa: BLE001
        # Fail over to mock so local demos keep working
        provider = get_call_provider("mock")
        result = await provider.start_call(
            callee_name=body.callee_name,
            to_number=body.to_number,
            agent_id=settings.ringg_agent_id,
            from_number_id=settings.ringg_from_number_id,
            custom_args=custom_args,
            callback_url=callback_url,
        )
        result.metadata["failover_reason"] = str(exc)

    call = Call(
        user_id=user.id,
        avatar_id=avatar.id if avatar else None,
        provider=result.provider,
        provider_call_id=result.provider_call_id,
        callee_name=body.callee_name,
        to_number=body.to_number,
        status=result.status,
        custom_args=custom_args,
        started_at=datetime.now(UTC),
    )
    db.add(call)
    await db.flush()
    return call, result


async def terminate_call(db: AsyncSession, user: User, call: Call) -> Call:
    if call.status in TERMINAL_STATUSES:
        return call
    provider = get_call_provider(call.provider)
    try:
        await provider.terminate_call(call.provider_call_id)
    except Exception:  # noqa: BLE001
        logger.warning("Provider terminate failed for %s", call.provider_call_id)
    call.status = "cancelled"
    call.ended_at = datetime.now(UTC)
    await db.flush()
    return call


async def apply_webhook_event(db: AsyncSession, event: dict) -> bool:
    """Apply a Ringg webhook event. Returns True when the event was new.

    Idempotent: dedupes on call_id + event_type via Call.processed_events.
    """
    provider_call_id = str(event.get("call_id") or "")
    event_type = str(event.get("event_type") or "")
    if not provider_call_id:
        return False

    call = (
        await db.execute(select(Call).where(Call.provider_call_id == provider_call_id))
    ).scalar_one_or_none()
    if not call:
        return False
    if call.status in TERMINAL_STATUSES:
        return False  # already final — late events must not overwrite results

    dedupe_key = f"{provider_call_id}:{event_type}"
    processed = list(call.processed_events or [])
    if dedupe_key in processed:
        return False
    processed.append(dedupe_key)
    call.processed_events = processed

    status_value = str(event.get("call_status") or event.get("status") or "")
    completed_event = event_type in ("call_completed", "all_processing_completed")
    if status_value == "completed" or (completed_event and status_value not in TERMINAL_STATUSES):
        call.status = "completed"
        call.ended_at = datetime.now(UTC)
        duration = event.get("duration") or event.get("call_duration") or 0
        try:
            call.duration_sec = int(duration)
        except (TypeError, ValueError):
            call.duration_sec = 0
        if event.get("transcript"):
            call.transcript = str(event["transcript"])
        if event.get("recording_url"):
            call.recording_url = str(event["recording_url"])
        analysis = event.get("analysis")
        if isinstance(analysis, dict):
            call.analysis = analysis
            summary = analysis.get("summary") or analysis.get("call_summary")
            if summary:
                call.summary = str(summary)
        # Quota accounting (round up minutes, same formula as end_session)
        if call.duration_sec > 0:
            minutes = max(1, (call.duration_sec + 59) // 60)
            owner = (
                await db.execute(select(User).where(User.id == call.user_id))
            ).scalar_one_or_none()
            if owner:
                owner.used_minutes = min(owner.quota_minutes, owner.used_minutes + minutes)
    elif status_value in TERMINAL_STATUSES:
        call.status = status_value
        call.ended_at = datetime.now(UTC)
    elif status_value:
        call.status = status_value

    await db.flush()
    return True


def schedule_mock_autocomplete(result: CallResult) -> None:
    """Mock calls have no real provider to report back — simulate Ringg's
    all_processing_completed webhook after a few seconds so demos complete
    end-to-end without manual curl."""
    if not result.mock_mode:
        return

    async def _auto_complete() -> None:
        # Late import: AsyncSessionLocal binds to the running loop
        from app.core.database import AsyncSessionLocal
        from app.providers.call_registry import get_call_provider

        await asyncio.sleep(MOCK_AUTOCOMPLETE_DELAY_SEC)
        mock = get_call_provider("mock")
        event = mock.simulate_completion(result.provider_call_id)
        try:
            async with AsyncSessionLocal() as db:
                await apply_webhook_event(db, event)
                await db.commit()
        except Exception:
            logger.exception("Mock call auto-complete failed")

    asyncio.create_task(_auto_complete())
