"""Gateway outbound reply and push protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from zero_agent.gateway.protocol import MessageEvent, PushTarget


class UnsupportedOutboundError(Exception):
    """Raised when an adapter lacks capability for an outbound operation."""


@dataclass(frozen=True)
class AdapterCapabilities:
    """Declared outbound features for graceful degradation in Dispatcher."""

    reply: bool = True
    reply_stream: bool = False
    push: bool = False
    approval_card: bool = False
    approval_card_update: bool = False


@dataclass(frozen=True)
class ApprovalRequest:
    """HITL approval card payload (Adapter-specific rendering)."""

    request_id: str
    title: str
    description: str = ""


class OutboundChannel(Protocol):
    """Unified outbound interface; platform adapters implement as needed."""

    capabilities: AdapterCapabilities

    async def reply(self, event: MessageEvent, content: str) -> None:
        """Short in-callback reply (WeCom: client.reply within ~5s)."""
        ...

    async def reply_stream(
        self,
        event: MessageEvent,
        stream_id: str,
        content: str,
        *,
        finish: bool = False,
    ) -> None:
        """Stream updates within callback window (WeCom: client.reply_stream)."""
        ...

    async def push(self, target: PushTarget, content: str) -> None:
        """Proactive push outside callback (WeCom: client.send_message)."""
        ...

    async def request_approval(self, event: MessageEvent, req: ApprovalRequest) -> None:
        """Send an approval card for human-in-the-loop."""
        ...

    async def update_approval(self, event: MessageEvent, req: ApprovalRequest) -> None:
        """Update an existing approval card."""
        ...
