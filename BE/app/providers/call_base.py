from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallResult:
    provider: str
    provider_call_id: str
    status: str = "registered"
    mock_mode: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class CallProvider(ABC):
    """Swappable telephony voice-call provider (Ringg, mock).

    Unlike AvatarProvider there is no live media channel: the provider owns
    the call end-to-end and reports results back via webhooks / polling.
    """

    name: str = "base"

    @abstractmethod
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
        ...

    @abstractmethod
    async def terminate_call(self, provider_call_id: str) -> None:
        ...

    async def health(self) -> str:
        return "up"
