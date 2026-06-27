"""HTTP / Webhook platform adapter (Phase 2)."""

from __future__ import annotations

from zero_agent.gateway.protocol import BaseAdapter


class HttpAdapter(BaseAdapter):
    """Placeholder adapter for self-hosted HTTP clients."""

    def __init__(self) -> None:
        super().__init__(name="http")

    async def connect(self) -> bool:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError
