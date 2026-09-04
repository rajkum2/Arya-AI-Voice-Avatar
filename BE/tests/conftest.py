import hashlib
import hmac
import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.call import Call

WEBHOOK_TOKEN = "test-webhook-token"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        yield c


async def register_and_consent(client: AsyncClient, consent: bool = True) -> dict:
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


async def get_provider_call_id(call_id: str) -> str:
    async with AsyncSessionLocal() as db:
        call = (
            await db.execute(select(Call).where(Call.id == uuid.UUID(call_id)))
        ).scalar_one()
        return call.provider_call_id


# ── Bolti webhook helpers ────────────────────────────────────────────

BOLTI_SECRET = "test-bolti-secret"


def bolti_headers(secret: str, raw: bytes, event_type: str, ts: int | None = None):
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
