import asyncio
import uuid

import pytest
from conftest import WEBHOOK_TOKEN, get_provider_call_id, register_and_consent
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.call import Call
from app.providers.call_registry import get_call_provider
from app.services import call_service


@pytest.mark.asyncio
async def test_create_call_mock_mode(client):
    headers = await register_and_consent(client)
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
    headers = await register_and_consent(client, consent=False)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_call_bad_number(client):
    headers = await register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "9876543210"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_mock_call_autocompletes(client, monkeypatch):
    monkeypatch.setattr(call_service, "MOCK_AUTOCOMPLETE_DELAY_SEC", 0.1)
    headers = await register_and_consent(client)
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
        headers = await register_and_consent(client)
        r = await client.post(
            "/api/v1/calls",
            headers=headers,
            json={"callee_name": "Rahul", "to_number": "+919876543210"},
        )
        assert r.status_code == 200, r.text
        call_id = r.json()["id"]
        provider_call_id = await get_provider_call_id(call_id)

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


async def _call_custom_args(call_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        call = (
            await db.execute(select(Call).where(Call.id == uuid.UUID(call_id)))
        ).scalar_one()
        return dict(call.custom_args or {})


async def _first_avatar_id(client: AsyncClient) -> str:
    r = await client.get("/api/v1/avatars")
    assert r.status_code == 200, r.text
    avatars = r.json()
    assert avatars, "seed should have created avatars"
    return avatars[0]["id"]


def test_provider_identity_is_per_provider(monkeypatch):
    """Regression: Bolti used to receive Ringg's agent id and from_number_id."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ringg_agent_id", "ringg-agent")
    monkeypatch.setattr(settings, "ringg_from_number_id", "ringg-number-uuid")
    monkeypatch.setattr(settings, "bolti_agent_id", "bolti-agent")
    monkeypatch.setattr(settings, "bolti_from_number", "+919999999999")

    assert call_service._provider_identity("ringg") == (
        "ringg-agent",
        "ringg-number-uuid",
    )
    assert call_service._provider_identity("bolti") == (
        "bolti-agent",
        "+919999999999",
    )
    assert call_service._provider_identity("mock") == ("", "")


@pytest.mark.asyncio
async def test_persona_flows_into_custom_args(client):
    headers = await register_and_consent(client)
    avatar_id = await _first_avatar_id(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={
            "avatar_id": avatar_id,
            "callee_name": "Rahul",
            "to_number": "+919876543210",
        },
    )
    assert r.status_code == 200, r.text

    args = await _call_custom_args(r.json()["id"])
    assert args["callee_name"] == "Rahul"
    # Persona reached the vendor payload instead of being loaded and dropped
    assert args["avatar_name"]
    assert args["greeting"]
    assert args["system_prompt"]


@pytest.mark.asyncio
async def test_explicit_custom_args_win_over_persona(client):
    headers = await register_and_consent(client)
    avatar_id = await _first_avatar_id(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={
            "avatar_id": avatar_id,
            "callee_name": "Rahul",
            "to_number": "+919876543210",
            "custom_args": {"greeting": "Custom opener"},
        },
    )
    assert r.status_code == 200, r.text

    args = await _call_custom_args(r.json()["id"])
    assert args["greeting"] == "Custom opener"
    assert args["avatar_name"]  # other persona fields still fill in


@pytest.mark.asyncio
async def test_persona_omitted_when_disabled(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "call_send_persona", False)
    headers = await register_and_consent(client)
    avatar_id = await _first_avatar_id(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={
            "avatar_id": avatar_id,
            "callee_name": "Rahul",
            "to_number": "+919876543210",
        },
    )
    assert r.status_code == 200, r.text

    args = await _call_custom_args(r.json()["id"])
    assert args == {"callee_name": "Rahul"}
