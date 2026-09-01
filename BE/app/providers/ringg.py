import httpx

from app.core.config import get_settings
from app.providers.call_base import CallProvider, CallResult


class RinggCallProvider(CallProvider):
    """Ringg AI outbound calling (https://docs.ringg.ai).

    NOTE: uses /calling/outbound/individual, which Ringg marks deprecated in
    favour of the number-pool v2 endpoint. It is kept here because it accepts
    an explicit from_number_id — simplest for a single-number setup. Swapping
    to v2 later is a one-function change.
    """

    name = "ringg"

    def _headers(self) -> dict[str, str]:
        return {"X-API-KEY": get_settings().ringg_api_key}

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
        settings = get_settings()
        payload = {
            "name": callee_name,
            "mobile_number": to_number,
            "agent_id": agent_id or settings.ringg_agent_id,
            "from_number_id": from_number_id or settings.ringg_from_number_id,
            "custom_args_values": custom_args,
            "callback_url": callback_url,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{settings.ringg_base_url}/calling/outbound/individual",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json().get("data") or {}
        return CallResult(
            provider=self.name,
            provider_call_id=str(data.get("call_id") or ""),
            status=str(data.get("call_status") or "registered"),
            mock_mode=False,
            metadata={"agent_id": data.get("agent_id") or payload["agent_id"]},
        )

    async def terminate_call(self, provider_call_id: str) -> None:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{settings.ringg_base_url}/calling/terminate",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"call_ids": [provider_call_id]},
            )
            resp.raise_for_status()

    async def health(self) -> str:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.ringg_base_url}/workspace", headers=self._headers()
                )
            return "up" if resp.status_code == 200 else "degraded"
        except Exception:  # noqa: BLE001
            return "down"
