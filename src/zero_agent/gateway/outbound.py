"""Gateway outbound reply protocol"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from zero_agent.gateway.protocol import MessageEvent


@dataclass(frozen=True)
class AdapterCapabilities:
    reply: bool = True


class OutboundChannel(Protocol):
    """Minimal outbound interface for short replies."""

    capabilities: AdapterCapabilities

    async def reply(self, event: MessageEvent, content: str) -> None: ...
