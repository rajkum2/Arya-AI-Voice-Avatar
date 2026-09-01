import hashlib
import hmac
import json
import time

import pytest

from app.core.config import get_settings

from test_calls import WEBHOOK_TOKEN, _register_and_consent, client  # noqa: F401

BOLTI_SECRET = "test-bolti-secret"


def _bolti_headers(secret: str, raw: bytes, event_type: str, ts: int | None = None):
    ts = ts if ts is not None else int(time.time())
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return {
        "X-Voiceai-Event": event_type,
        "X-Voiceai-Signature": f"t={ts},v1={digest}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def bolti_secret():
    settings = get_settings()
    original = settings.bolti_webhook_secret
    settings.bolti_webhook_secret = BOLTI_SECRET
    yield BOLTI_SECRET
    settings.bolti_webhook_secret = original


@pytest.mark.asyncio
async def test_bolti_unconfigured_falls_back_to_mock(client):
    headers = await _register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={
            "callee_name": "Rahul",
            "to_number": "+919876543210",
            "provider": "bolti",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["mock_mode"] is True
    assert r.json()["provider"] == "mock"


@pytest.mark.asyncio
async def test_bolti_webhook_signature_and_completion(client, bolti_secret):
    headers = await _register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210", "provider": "bolti"},
    )
    assert r.status_code == 200, r.text
    call_id = r.json()["id"]

    # Mock provider made the call (Bolti unconfigured) — reuse its id as the
    # conversation_id, since the webhook matches on provider_call_id.
    from test_calls import _provider_call_id

    conversation_id = await _provider_call_id(call_id)

    payload = {
        "id": "evt_bolti_1",
        "conversation_id": conversation_id,
        "duration_sec": 75,
        "transcript": "assistant: Hi Rahul\nuser: Confirm",
        "recording_url": "https://example.com/rec.mp3",
        "summary": "Appointment confirmed.",
    }
    raw = json.dumps(payload).encode()

    # Bad signature rejected
    r = await client.post(
        "/api/v1/webhooks/bolti",
        headers={**_bolti_headers(bolti_secret, raw, "conversation.completed"),
                 "X-Voiceai-Signature": f"t={int(time.time())},v1=deadbeef"},
        content=raw,
    )
    assert r.status_code == 401

    # Stale timestamp rejected (>5 min replay window)
    r = await client.post(
        "/api/v1/webhooks/bolti",
        headers=_bolti_headers(bolti_secret, raw, "conversation.completed",
                               ts=int(time.time()) - 600),
        content=raw,
    )
    assert r.status_code == 401

    # Valid signature applies the completion
    r = await client.post(
        "/api/v1/webhooks/bolti",
        headers=_bolti_headers(bolti_secret, raw, "conversation.completed"),
        content=raw,
    )
    assert r.status_code == 204

    r = await client.get(f"/api/v1/calls/{call_id}", headers=headers)
    body = r.json()
    assert body["status"] == "completed"
    assert body["duration_sec"] == 75
    assert "Confirm" in body["transcript"]
    assert body["recording_url"] == "https://example.com/rec.mp3"
    assert body["summary"] == "Appointment confirmed."

    # Replay with same event id is deduped — no double quota
    r = await client.get("/api/v1/auth/me", headers=headers)
    used = r.json()["used_minutes"]
    r = await client.post(
        "/api/v1/webhooks/bolti",
        headers=_bolti_headers(bolti_secret, raw, "conversation.completed"),
        content=raw,
    )
    assert r.status_code == 204
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.json()["used_minutes"] == used
