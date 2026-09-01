from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.call import Call
from app.schemas.call import CallCreateRequest, CallOut
from app.services.call_service import (
    apply_webhook_event,
    create_call,
    schedule_mock_autocomplete,
    terminate_call,
)

router = APIRouter(tags=["calls"])


def _to_out(call: Call, mock_mode: bool | None = None) -> CallOut:
    return CallOut(
        id=call.id,
        avatar_id=call.avatar_id,
        provider=call.provider,
        status=call.status,
        callee_name=call.callee_name,
        to_number=call.to_number,
        duration_sec=call.duration_sec,
        transcript=call.transcript,
        summary=call.summary,
        recording_url=call.recording_url,
        analysis=call.analysis or {},
        mock_mode=call.provider == "mock" if mock_mode is None else mock_mode,
        created_at=call.created_at,
        ended_at=call.ended_at,
    )


@router.post("/calls", response_model=CallOut)
async def start_call(
    body: CallCreateRequest, request: Request, user: CurrentUser, db: DbSession
) -> CallOut:
    callback_base = str(request.base_url)
    call, result = await create_call(db, user, body, callback_base)
    schedule_mock_autocomplete(result)
    return _to_out(call, mock_mode=result.mock_mode)


@router.get("/calls", response_model=list[CallOut])
async def list_calls(user: CurrentUser, db: DbSession) -> list[CallOut]:
    rows = (
        await db.execute(
            select(Call)
            .where(Call.user_id == user.id)
            .order_by(Call.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return [_to_out(c) for c in rows]


@router.get("/calls/{call_id}", response_model=CallOut)
async def get_call(call_id: UUID, user: CurrentUser, db: DbSession) -> CallOut:
    call = (
        await db.execute(select(Call).where(Call.id == call_id))
    ).scalar_one_or_none()
    if not call or call.user_id != user.id:
        raise HTTPException(status_code=404, detail="Call not found")
    return _to_out(call)


@router.delete("/calls/{call_id}", response_model=CallOut)
async def cancel_call(call_id: UUID, user: CurrentUser, db: DbSession) -> CallOut:
    call = (
        await db.execute(select(Call).where(Call.id == call_id))
    ).scalar_one_or_none()
    if not call or call.user_id != user.id:
        raise HTTPException(status_code=404, detail="Call not found")
    call = await terminate_call(db, user, call)
    return _to_out(call)


@router.post("/webhooks/ringg", status_code=204)
async def ringg_webhook(request: Request, db: DbSession) -> None:
    """Ringg event receiver. Secured by the shared bearer token that Ringg
    forwards from the assistant's event-subscription headers (no signatures
    offered by Ringg)."""
    settings = get_settings()
    if not settings.ringg_webhook_token:
        raise HTTPException(status_code=503, detail="Webhook token not configured")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {settings.ringg_webhook_token}":
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    event = await request.json()
    await apply_webhook_event(db, event)
    return None
