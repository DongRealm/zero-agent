"""Inbound message routing (Command / Agent branches added in later phases)."""

from __future__ import annotations

import asyncio

from zero_agent.gateway.protocol import MessageEvent


class MessageDispatcher:
    """Routes inbound messages to handlers.

    Phase A skeleton: echo only. Command and Agent branches wire in Phase F.
    """

    async def handle(self, event: MessageEvent) -> str | None:
        """Process one inbound message. Returns reply text for the adapter."""
        await asyncio.sleep(1.0)
        return f"已收到消息: {event.content}"
