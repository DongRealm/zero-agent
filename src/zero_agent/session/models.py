"""Session identity and persisted registry records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from zero_agent.gateway.protocol import MessageEvent


class ThreadStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass(frozen=True)
class SessionKey:
    platform: str
    chat_id: str
    user_id: str | None = None

    def to_id(self) -> str:
        """Registry primary key; must match MessageEvent.session_id."""
        if not self.chat_id:
            return f"{self.platform}:unknown"
        if self.user_id:
            return f"{self.platform}:{self.chat_id}:{self.user_id}"
        return f"{self.platform}:{self.chat_id}"

    @classmethod
    def from_id(cls, session_id: str) -> SessionKey:
        parts = session_id.split(":", 2)
        if not parts or not parts[0]:
            raise ValueError(f"invalid session_id: {session_id!r}")

        platform = parts[0]
        if len(parts) == 1:
            return cls(platform=platform, chat_id="")

        if len(parts) == 2:
            chat_token = parts[1]
            if chat_token == "unknown":
                return cls(platform=platform, chat_id="")
            return cls(platform=platform, chat_id=chat_token)

        chat_id, user_id = parts[1], parts[2]
        return cls(platform=platform, chat_id=chat_id, user_id=user_id or None)

    @classmethod
    def from_event(cls, event: MessageEvent) -> SessionKey:
        if event.session_id:
            return cls.from_id(event.session_id)
        return cls(platform=event.platform, chat_id="")


@dataclass
class SessionThreadRecord:
    """One conversation thread line under a session."""

    thread_id: str
    session_id: str
    generation: int
    status: ThreadStatus
    started_at: datetime
    ended_at: datetime | None = None


@dataclass
class SessionRecord:
    """Current session pointer; active thread lives in session_threads."""

    key: SessionKey
    active_thread_id: str
    locale: str = "zh"
    generation: int = 1
    last_active_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def session_id(self) -> str:
        return self.key.to_id()

    @property
    def thread_id(self) -> str:
        """Alias for the active LangGraph thread_id."""
        return self.active_thread_id

    def touch(self, at: datetime | None = None) -> SessionRecord:
        return SessionRecord(
            key=self.key,
            active_thread_id=self.active_thread_id,
            locale=self.locale,
            generation=self.generation,
            last_active_at=at or datetime.now(UTC),
            metadata=dict(self.metadata),
        )
