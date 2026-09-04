"""Edge-case coverage for the phone-call channel: cancel, list, webhook
auth-when-unconfigured, unknown call ids, and non-completion statuses."""

import json

import pytest
from conftest import WEBHOOK_TOKEN, bolti_headers, get_provider_call_id, register_and_consent

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_list_calls_returns_only_mine(client):
    headers = await register_and_consent(client)
    await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    r = await client.get("/api/v1/calls", headers=headers)
    assert r.status_code == 200
    calls = r.json()
    assert len(calls) >= 1
    assert all(c["callee_name"] for c in calls)

    # Another user's view does not include this call
    other = await register_and_consent(client)
    r = await client.get("/api/v1/calls", headers=other)
    assert all(c["to_number"] != "+919876543210" or c["callee_name"] != "Rahul"
               for c in r.json())


@pytest.mark.asyncio
async def test_cancel_call(client):
    headers = await register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    call_id = r.json()["id"]

    r = await client.delete(f"/api/v1/calls/{call_id}", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    assert r.json()["ended_at"] is not None

    # Cancelling again is a harmless no-op
    r = await client.delete(f"/api/v1/calls/{call_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_other_users_call_forbidden(client):
    headers = await register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    call_id = r.json()["id"]

    other = await register_and_consent(client)
    r = await client.delete(f"/api/v1/calls/{call_id}", headers=other)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ringg_webhook_rejected_when_token_unset(client):
    settings = get_settings()
    original = settings.ringg_webhook_token
    settings.ringg_webhook_token = ""
    try:
        r = await client.post("/api/v1/webhooks/ringg", json={"call_id": "x"})
        assert r.status_code == 503
    finally:
        settings.ringg_webhook_token = original


@pytest.mark.asyncio
async def test_bolti_webhook_rejected_when_secret_unset(client):
    settings = get_settings()
    original = settings.bolti_webhook_secret
    settings.bolti_webhook_secret = ""
    try:
        r = await client.post(
            "/api/v1/webhooks/bolti",
            headers={"X-Voiceai-Event": "conversation.completed"},
            content=b"{}",
        )
        assert r.status_code == 503
    finally:
        settings.bolti_webhook_secret = original


@pytest.mark.asyncio
async def test_webhook_unknown_call_is_noop(client):
    settings = get_settings()
    original = settings.ringg_webhook_token
    settings.ringg_webhook_token = WEBHOOK_TOKEN
    try:
        r = await client.post(
            "/api/v1/webhooks/ringg",
            headers={"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            json={
                "call_id": "nonexistent-call-id",
                "event_type": "all_processing_completed",
                "call_status": "completed",
            },
        )
        assert r.status_code == 204  # ack anyway so providers don't retry forever
    finally:
        settings.ringg_webhook_token = original


@pytest.mark.asyncio
async def test_webhook_failure_statuses(client):
    settings = get_settings()
    original = settings.ringg_webhook_token
    settings.ringg_webhook_token = WEBHOOK_TOKEN
    try:
        headers = await register_and_consent(client)
        r = await client.post(
            "/api/v1/calls",
            headers=headers,
            json={"callee_name": "Rahul", "to_number": "+919876543210"},
        )
        call_id = r.json()["id"]
        provider_call_id = await get_provider_call_id(call_id)

        # In-progress event updates status without touching anything else
        r = await client.post(
            "/api/v1/webhooks/ringg",
            headers={"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            json={"call_id": provider_call_id, "event_type": "call_started",
                  "call_status": "ongoing"},
        )
        assert r.status_code == 204
        r = await client.get(f"/api/v1/calls/{call_id}", headers=headers)
        assert r.json()["status"] == "ongoing"

        # Failed event terminates the call
        r = await client.post(
            "/api/v1/webhooks/ringg",
            headers={"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            json={"call_id": provider_call_id, "event_type": "call_completed",
                  "call_status": "failed"},
        )
        assert r.status_code == 204
        r = await client.get(f"/api/v1/calls/{call_id}", headers=headers)
        assert r.json()["status"] == "failed"
        assert r.json()["ended_at"] is not None
    finally:
        settings.ringg_webhook_token = original


@pytest.mark.asyncio
async def test_bolti_non_completion_event_is_noop(client, bolti_secret):
    payload = {"id": "evt_x", "conversation_id": "unknown-conv"}
    raw = json.dumps(payload).encode()
    r = await client.post(
        "/api/v1/webhooks/bolti",
        headers=bolti_headers(bolti_secret, raw, "scheduled_call.created"),
        content=raw,
    )
    assert r.status_code == 204
