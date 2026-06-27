from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    """Message type enumeration."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    UNKNOWN = "unknown"


@dataclass
class MessageEvent:
    """Unified message event abstraction."""

    platform: str
    """Source platform, e.g. wecom."""

    content: str
    """Message content (text content for text messages)."""

    msg_type: MessageType = MessageType.TEXT
    """Message type."""

    extra: dict[str, Any] | None = None
    """Extended fields, e.g. @ mentions, reply context, etc."""


MessageHandler = Callable[[MessageEvent], Awaitable[str | None]]


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

        Target signature: ``async def handler(event: MessageEvent) -> None``
        Replies should be sent via ``OutboundChannel.reply`` (Phase F).

        Transitional: handlers may still return ``str | None``; non-empty values
        are sent via ``_send_reply`` until Phase F step 23.
        """
        self._message_handler = handler

    async def handle_message(self, event: MessageEvent) -> None:
        """Entry point for incoming messages, handles session queuing.

        Only one message per session is processed at a time; subsequent messages
        are queued and processed sequentially.
        """
        session_key = f"{event.platform}"

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
            reply = await self._dispatch(event)
            if reply:
                await self._send_reply(event, reply)

            while session_key in self._pending_messages and self._pending_messages[session_key]:
                next_event = self._pending_messages[session_key].pop(0)
                reply = await self._dispatch(next_event)
                if reply:
                    await self._send_reply(next_event, reply)
        finally:
            self._active_sessions.pop(session_key, None)
            self._pending_messages.pop(session_key, None)

    async def _send_reply(self, _event: MessageEvent, reply: str) -> None:
        """Send a reply. Subclasses can override this for platform-specific reply logic.

        Default implementation prints to console.
        """
        print(f"  [{self.name}] {reply}")

    async def _dispatch(self, event: MessageEvent) -> str | None:
        """Dispatch the message event to the handler."""
        if self._message_handler:
            result: str | None = await self._message_handler(event)
            return result
        return None
