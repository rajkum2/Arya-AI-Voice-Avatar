import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.services.call_service as call_service
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.call import Call
from app.providers.call_registry import get_call_provider

WEBHOOK_TOKEN = "test-webhook-token"


async def _register_and_consent(client: AsyncClient, consent: bool = True) -> dict:
    email = f"calltest-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "Call Test"},
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if consent:
        r = await client.post(
            "/api/v1/auth/consent",
            headers=headers,
            json={
                "understand_ai": True,
                "voice_processing": True,
                "store_transcripts": True,
                "improve_service": False,
            },
        )
        assert r.status_code == 200, r.text
    return headers


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_create_call_mock_mode(client):
    headers = await _register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "registered"
    assert body["mock_mode"] is True
    assert body["provider"] == "mock"


@pytest.mark.asyncio
async def test_create_call_requires_consent(client):
    headers = await _register_and_consent(client, consent=False)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_call_bad_number(client):
    headers = await _register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "9876543210"},
    )
    assert r.status_code == 422


async def _provider_call_id(call_id: str) -> str:
    async with AsyncSessionLocal() as db:
        call = (
            await db.execute(select(Call).where(Call.id == uuid.UUID(call_id)))
        ).scalar_one()
        return call.provider_call_id


@pytest.mark.asyncio
async def test_mock_call_autocompletes(client, monkeypatch):
    monkeypatch.setattr(call_service, "MOCK_AUTOCOMPLETE_DELAY_SEC", 0.1)
    headers = await _register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Priya", "to_number": "+919123456780"},
    )
    assert r.status_code == 200, r.text
    call_id = r.json()["id"]
    assert r.json()["status"] == "registered"

    await asyncio.sleep(1.0)  # let the background auto-complete task fire

    r = await client.get(f"/api/v1/calls/{call_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert "mock Arya call" in r.json()["transcript"]


@pytest.mark.asyncio
async def test_webhook_flow_and_idempotency(client):
    settings = get_settings()
    original_token = settings.ringg_webhook_token
    settings.ringg_webhook_token = WEBHOOK_TOKEN
    try:
        headers = await _register_and_consent(client)
        r = await client.post(
            "/api/v1/calls",
            headers=headers,
            json={"callee_name": "Rahul", "to_number": "+919876543210"},
        )
        assert r.status_code == 200, r.text
        call_id = r.json()["id"]
        provider_call_id = await _provider_call_id(call_id)

        mock = get_call_provider("mock")
        event = mock.simulate_completion(provider_call_id)

        # Wrong token rejected
        r = await client.post(
            "/api/v1/webhooks/ringg",
            headers={"Authorization": "Bearer wrong"},
            json=event,
        )
        assert r.status_code == 401

        # Correct token applies the result
        r = await client.post(
            "/api/v1/webhooks/ringg",
            headers={"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            json=event,
        )
        assert r.status_code == 204

        r = await client.get(f"/api/v1/calls/{call_id}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "completed"
        assert "mock Arya call" in body["transcript"]
        assert body["duration_sec"] == 42

        r = await client.get("/api/v1/auth/me", headers=headers)
        used_after_first = r.json()["used_minutes"]
        assert used_after_first == 1  # 42s rounds up to 1 minute

        # Replay of the same event is deduped — no double quota
        r = await client.post(
            "/api/v1/webhooks/ringg",
            headers={"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            json=event,
        )
        assert r.status_code == 204
        r = await client.get("/api/v1/auth/me", headers=headers)
        assert r.json()["used_minutes"] == used_after_first
    finally:
        settings.ringg_webhook_token = original_token
