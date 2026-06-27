from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from zero_agent.observability.setup import get_logger


class MessageType(StrEnum):
    """Message type enumeration."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PushTarget:
    """Destination for proactive outbound pushes (e.g. WeCom send_message)."""

    chat_id: str
    chat_type: int | None = None
    """WeCom: 1 = direct chat, 2 = group chat."""


@dataclass
class MessageEvent:
    """Unified message event abstraction."""

    platform: str
    """Source platform, e.g. wecom."""

    content: str
    """Message content (text content for text messages)."""

    session_id: str = ""
    """Per-user/chat session key for queuing; must equal SessionKey.to_id()."""

    msg_type: MessageType = MessageType.TEXT
    """Message type."""

    push_target: PushTarget = field(default_factory=lambda: PushTarget(chat_id=""))
    """Target for proactive push notifications."""

    reply_to: dict[str, Any] = field(default_factory=dict)
    """Platform frame/context required for in-callback reply or reply_stream."""

    extra: dict[str, Any] | None = None
    """Extended fields, e.g. @ mentions, reply context, etc."""


MessageHandler = Callable[[MessageEvent], Awaitable[None]]

logger = get_logger(__name__)


class BaseAdapter(ABC):
    """Base class for platform adapters."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._message_handler: MessageHandler | None = None
        self._active_sessions: dict[str, asyncio.Event] = {}
        self._pending_messages: dict[str, list[MessageEvent]] = {}

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection. Returns True on success, False on failure."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect."""
        ...

    def set_message_handler(self, handler: MessageHandler | Any) -> None:
        """Set the message handler.

        Signature: ``async def handler(event: MessageEvent) -> None``
        Replies must be sent via ``OutboundChannel.reply`` inside the handler chain.
        """
        self._message_handler = handler

    async def handle_message(self, event: MessageEvent) -> None:
        """Entry point for incoming messages, handles session queuing.

        Only one message per session is processed at a time; subsequent messages
        are queued and processed sequentially.
        """
        session_key = event.session_id or event.platform

        if session_key in self._active_sessions:
            if session_key not in self._pending_messages:
                self._pending_messages[session_key] = []
            self._pending_messages[session_key].append(event)
            return

        self._active_sessions[session_key] = asyncio.Event()
        asyncio.create_task(self._process_session(event, session_key))

    async def _process_session(self, event: MessageEvent, session_key: str) -> None:
        """Process the current message, then consume queued messages in order."""
        try:
            await self._dispatch(event)

            while session_key in self._pending_messages and self._pending_messages[session_key]:
                next_event = self._pending_messages[session_key].pop(0)
                await self._dispatch(next_event)
        finally:
            self._active_sessions.pop(session_key, None)
            self._pending_messages.pop(session_key, None)

    async def _send_reply(self, _event: MessageEvent, reply: str) -> None:
        """Send a reply. Subclasses can override this for platform-specific reply logic.

        Default implementation logs the reply (platform adapters should override).
        """
        logger.info(
            "gateway.reply",
            platform=self.name,
            session_id=_event.session_id or None,
            content_len=len(reply),
        )

    async def _dispatch(self, event: MessageEvent) -> None:
        """Dispatch the message event to the handler."""
        if self._message_handler:
            await self._message_handler(event)
