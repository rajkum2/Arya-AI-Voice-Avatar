import httpx

from app.core.config import get_settings
from app.providers.call_base import CallProvider, CallResult


class BoltiCallProvider(CallProvider):
    """Bolti AI outbound calling (https://docs.bolti.co.in).

    Webhooks are workspace-level (configured in the Bolti dashboard), so
    start_call ignores the per-call callback_url used by Ringg.
    """

    name = "bolti"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {get_settings().bolti_token}"}

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
        custom_variables = {"customer_name": callee_name, **custom_args}
        payload = {
            "agent_id": agent_id or settings.bolti_agent_id,
            "to_number": to_number,
            # Bolti takes a literal E.164 number, not a from_number_id
            "from_number": from_number_id or settings.bolti_from_number,
            "custom_variables": custom_variables,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{settings.bolti_base_url}/calls",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                # Surface Bolti's error body (402 credits, 403 number not assigned...)
                raise RuntimeError(f"Bolti {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
        return CallResult(
            provider=self.name,
            provider_call_id=str(data.get("conversation_id") or ""),
            status="registered",
            mock_mode=False,
            metadata={"agent_id": payload["agent_id"]},
        )

    async def terminate_call(self, provider_call_id: str) -> None:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{settings.bolti_base_url}/calls/{provider_call_id}/cancel",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return  # already terminal / unknown — cancel is best-effort
            resp.raise_for_status()

    async def health(self) -> str:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.bolti_base_url}/agents",
                    headers=self._headers(),
                    params={"limit": 1},
                )
            return "up" if resp.status_code == 200 else "degraded"
        except Exception:  # noqa: BLE001
            return "down"
