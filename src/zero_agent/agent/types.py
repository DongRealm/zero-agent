"""Public agent result and error types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentResult:
    content: str
    thread_id: str


class AgentError(Exception):
    """Raised when agent invocation fails."""

    def __init__(self, message: str, *, thread_id: str | None = None) -> None:
        super().__init__(message)
        self.thread_id = thread_id
