"""Feishu platform adapter (Phase 2)."""

from __future__ import annotations

from zero_agent.gateway.protocol import BaseAdapter


class FeishuAdapter(BaseAdapter):
    """Placeholder adapter for Feishu integration."""

    def __init__(self) -> None:
        super().__init__(name="feishu")

    async def connect(self) -> bool:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError
