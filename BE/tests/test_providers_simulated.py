"""Simulated end-to-end tests against the DOCUMENTED Ringg/Bolti API shapes
(voice-calling-agent.md). No real keys or numbers: httpx.MockTransport stands
in for the provider and asserts we send exactly what their docs expect, and
parse exactly what their docs promise back.

Ringg  : POST /calling/outbound/individual, X-API-KEY header,
         body {name, mobile_number, agent_id, from_number_id,
               custom_args_values, callback_url}
         resp {"status":"success","data":{"call_id","call_status",...}}
Bolti  : POST /calls, Bearer PAT,
         body {agent_id, to_number, from_number, custom_variables}
         resp {"conversation_id": ...}; errors 400/402/403/404/409/429
"""

import json

import httpx
import pytest
from conftest import register_and_consent

from app.core.config import get_settings
from app.providers.bolti import BoltiCallProvider
from app.providers.ringg import RinggCallProvider

# ── helpers ──────────────────────────────────────────────────────────


def _patch_httpx(monkeypatch, handler):
    """Route every httpx.AsyncClient through a MockTransport handler."""
    real = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return real(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.fixture
def ringg_configured():
    s = get_settings()
    saved = (s.ringg_api_key, s.ringg_agent_id, s.ringg_from_number_id)
    s.ringg_api_key = "test-ringg-key"
    s.ringg_agent_id = "agent-123"
    s.ringg_from_number_id = "num-456"
    yield s
    s.ringg_api_key, s.ringg_agent_id, s.ringg_from_number_id = saved


@pytest.fixture
def bolti_configured():
    s = get_settings()
    saved = (s.bolti_token, s.bolti_agent_id, s.bolti_from_number)
    s.bolti_token = "test-bolti-pat"
    s.bolti_agent_id = "agent-789"
    s.bolti_from_number = "+917969541371"
    yield s
    s.bolti_token, s.bolti_agent_id, s.bolti_from_number = saved


# ── Ringg provider unit-level ────────────────────────────────────────


@pytest.mark.asyncio
async def test_ringg_start_call_matches_documented_api(monkeypatch, ringg_configured):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("X-API-KEY")
        captured["body"] = json.loads(request.content)
        # Documented response shape (guide §5 step ④)
        return httpx.Response(200, json={
            "status": "success",
            "data": {
                "call_id": "31106b7c-9d02-4723-8b07-5bb8d90240cb",
                "call_direction": "outbound",
                "call_status": "registered",
                "initiated_at": "2025-11-24T07:33:49.629642",
                "agent_id": "agent-123",
            },
            "message": "Call initiated successfully",
        })

    _patch_httpx(monkeypatch, handler)
    result = await RinggCallProvider().start_call(
        callee_name="Rahul Sharma",
        to_number="+919876543210",
        agent_id="",
        from_number_id="",
        custom_args={"callee_name": "Rahul", "appointment_date": "Tuesday 10 AM"},
        callback_url="https://example.com/api/v1/webhooks/ringg",
    )

    assert captured["url"] == (
        "https://prod-api.ringg.ai/ca/api/v0/calling/outbound/individual"
    )
    assert captured["api_key"] == "test-ringg-key"
    body = captured["body"]
    assert body["name"] == "Rahul Sharma"
    assert body["mobile_number"] == "+919876543210"
    # exactly from_number_id, never both (documented rule)
    assert body["from_number_id"] == "num-456"
    assert "from_number" not in body
    assert body["custom_args_values"]["appointment_date"] == "Tuesday 10 AM"
    assert body["callback_url"].endswith("/api/v1/webhooks/ringg")

    assert result.provider == "ringg"
    assert result.provider_call_id == "31106b7c-9d02-4723-8b07-5bb8d90240cb"
    assert result.status == "registered"
    assert result.mock_mode is False


@pytest.mark.asyncio
async def test_ringg_start_call_raises_on_documented_errors(
    monkeypatch, ringg_configured
):
    # 401 bad key / 429 rate limited — provider must raise so service fails over
    _patch_httpx(monkeypatch, lambda req: httpx.Response(
        401, json={"error": {"code": "invalid_key", "message": "bad key"}}
    ))
    with pytest.raises(httpx.HTTPStatusError):
        await RinggCallProvider().start_call(
            callee_name="R", to_number="+919876543210", agent_id="",
            from_number_id="", custom_args={}, callback_url="",
        )


@pytest.mark.asyncio
async def test_ringg_terminate_sends_call_ids(monkeypatch, ringg_configured):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success"})

    _patch_httpx(monkeypatch, handler)
    await RinggCallProvider().terminate_call("call-abc")
    assert captured["body"] == {"call_ids": ["call-abc"]}


# ── Bolti provider unit-level ────────────────────────────────────────


@pytest.mark.asyncio
async def test_bolti_start_call_matches_documented_api(monkeypatch, bolti_configured):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"conversation_id": "conv-abc-123"})

    _patch_httpx(monkeypatch, handler)
    result = await BoltiCallProvider().start_call(
        callee_name="Rahul",
        to_number="+919876543210",
        agent_id="",
        from_number_id="",
        custom_args={"appointment_date": "Tuesday 10 AM"},
        callback_url="https://unused.example.com",  # Bolti: workspace-level webhooks
    )

    assert captured["url"] == "https://api.bolti.co.in/v1/calls"
    assert captured["auth"] == "Bearer test-bolti-pat"
    body = captured["body"]
    assert body["agent_id"] == "agent-789"
    assert body["to_number"] == "+919876543210"
    # Bolti takes a literal E.164 number, unlike Ringg's from_number_id
    assert body["from_number"] == "+917969541371"
    assert body["custom_variables"]["customer_name"] == "Rahul"
    assert body["custom_variables"]["appointment_date"] == "Tuesday 10 AM"

    assert result.provider == "bolti"
    assert result.provider_call_id == "conv-abc-123"
    assert result.mock_mode is False


@pytest.mark.asyncio
async def test_bolti_start_call_raises_with_error_body(monkeypatch, bolti_configured):
    # 402 insufficient credits — message must be surfaced for failover logging
    _patch_httpx(monkeypatch, lambda req: httpx.Response(
        402, json={"error": {"code": "insufficient_credits"}}
    ))
    with pytest.raises(RuntimeError, match="402"):
        await BoltiCallProvider().start_call(
            callee_name="R", to_number="+919876543210", agent_id="",
            from_number_id="", custom_args={}, callback_url="",
        )


@pytest.mark.asyncio
async def test_bolti_terminate_swallows_404(monkeypatch, bolti_configured):
    _patch_httpx(monkeypatch, lambda req: httpx.Response(404, json={}))
    await BoltiCallProvider().terminate_call("conv-gone")  # must not raise


# ── End-to-end via API with configured (simulated) providers ─────────


@pytest.mark.asyncio
async def test_api_call_uses_real_ringg_provider(monkeypatch, client, ringg_configured):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "status": "success",
            "data": {"call_id": "ringg-live-1", "call_status": "registered"},
        })

    _patch_httpx(monkeypatch, handler)
    headers = await register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "ringg"      # real provider, NOT mock
    assert body["mock_mode"] is False
    assert body["status"] == "registered"


@pytest.mark.asyncio
async def test_api_call_uses_real_bolti_provider(
    monkeypatch, client, bolti_configured
):
    _patch_httpx(monkeypatch, lambda req: httpx.Response(
        200, json={"conversation_id": "bolti-live-1"}
    ))
    headers = await register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210", "provider": "bolti"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["provider"] == "bolti"
    assert r.json()["mock_mode"] is False


@pytest.mark.asyncio
async def test_api_failover_to_mock_when_ringg_errors(
    monkeypatch, client, ringg_configured
):
    # Ringg fully configured but returns 500 → service must fall back to mock
    _patch_httpx(monkeypatch, lambda req: httpx.Response(
        500, json={"error": {"code": "server_error"}}
    ))
    headers = await register_and_consent(client)
    r = await client.post(
        "/api/v1/calls",
        headers=headers,
        json={"callee_name": "Rahul", "to_number": "+919876543210"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mock_mode"] is True
    assert body["provider"] == "mock"
