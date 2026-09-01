import uuid
from typing import Any

from app.providers.call_base import CallProvider, CallResult


class MockCallProvider(CallProvider):
    """Local mock for development without a Ringg API key."""

    name = "mock"

    def __init__(self) -> None:
        self._calls: dict[str, dict[str, Any]] = {}

    async def start_call(
        self,
        *,
        callee_name: str,
        to_number: str,
        agent_id: str,
        from_number_id: str,
        custom_args: dict[str, str],
        callback_url: str,
    ) -> CallResult:
        cid = f"mock_call_{uuid.uuid4().hex[:12]}"
        self._calls[cid] = {
            "callee_name": callee_name,
            "to_number": to_number,
            "agent_id": agent_id,
            "custom_args": custom_args,
            "callback_url": callback_url,
        }
        return CallResult(
            provider=self.name,
            provider_call_id=cid,
            status="registered",
            mock_mode=True,
            metadata={"agent_id": agent_id},
        )

    async def terminate_call(self, provider_call_id: str) -> None:
        self._calls.pop(provider_call_id, None)

    def simulate_completion(self, provider_call_id: str) -> dict[str, Any]:
        """Build a fake `all_processing_completed` webhook payload for tests/demos."""
        store = self._calls.get(provider_call_id, {})
        name = store.get("callee_name") or "there"
        return {
            "call_id": provider_call_id,
            "event_type": "all_processing_completed",
            "call_status": "completed",
            "duration": 42,
            "transcript": (
                f"assistant: Hi {name}, this is a mock Arya call.\n"
                "user: Hello!\n"
                "assistant: This is a simulated transcript while Ringg is not configured."
            ),
            "recording_url": "",
            "analysis": {"summary": "Mock call completed successfully."},
        }
