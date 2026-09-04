import hashlib
import hmac
import time
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


def _verify_bolti_signature(raw: bytes, header: str, secret: str) -> bool:
    """Bolti HMAC-SHA256: header is 't=<unix_ts>,v1=<hex>[,v1=<hex>]';
    digest is HMAC(secret, '<ts>.<raw_body>'). Multiple v1 values are sent
    during secret rotation — accept if ANY matches."""
    try:
        parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
        ts = parts.get("t", "")
        if abs(time.time() - int(ts)) > 300:  # replay protection
            return False
    except (ValueError, AttributeError):
        return False
    expected = hmac.new(
        secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256
    ).hexdigest()
    digests = [p[3:] for p in header.split(",") if p.startswith("v1=")]
    return any(hmac.compare_digest(expected, d) for d in digests)


def _normalize_bolti_event(event_type: str, payload: dict) -> dict:
    """Map a Bolti webhook onto the generic shape apply_webhook_event expects."""
    conversation_id = str(
        payload.get("conversation_id")
        or (payload.get("conversation") or {}).get("id")
        or ""
    )
    event: dict = {
        "call_id": conversation_id,
        # Dedupe on the durable event id when present, else fall back
        "event_type": str(payload.get("id") or f"{conversation_id}:{event_type}"),
    }
    if event_type == "conversation.completed":
        event["call_status"] = "completed"
        event["duration"] = payload.get("duration_sec") or payload.get("duration") or 0
        if payload.get("transcript"):
            event["transcript"] = payload["transcript"]
        if payload.get("recording_url"):
            event["recording_url"] = payload["recording_url"]
        analysis = payload.get("analysis") or payload.get("summary")
        if isinstance(analysis, dict):
            event["analysis"] = analysis
        elif isinstance(analysis, str) and analysis:
            event["analysis"] = {"summary": analysis}
    elif event_type == "scheduled_call.failed":
        event["call_status"] = "failed"
    elif event_type == "scheduled_call.cancelled":
        event["call_status"] = "cancelled"
    # other events (scheduled_call.created/dispatched, campaign.completed) → no-op
    return event


@router.post("/webhooks/bolti", status_code=204)
async def bolti_webhook(request: Request, db: DbSession) -> None:
    """Bolti event receiver. Verifies the HMAC-SHA256 signature over the RAW
    body (re-serialized JSON would not match)."""
    settings = get_settings()
    if not settings.bolti_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    raw = await request.body()
    signature = request.headers.get("X-Voiceai-Signature", "")
    if not _verify_bolti_signature(raw, signature, settings.bolti_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-Voiceai-Event", "")
    payload = await request.json()
    event = _normalize_bolti_event(event_type, payload)
    if event.get("call_id") and event.get("call_status"):
        await apply_webhook_event(db, event)
