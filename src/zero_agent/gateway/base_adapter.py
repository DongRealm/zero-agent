"""Backward-compatible re-exports. Prefer zero_agent.gateway.protocol."""

from zero_agent.gateway.protocol import (
    BaseAdapter,
    MessageEvent,
    MessageHandler,
    MessageType,
    PushTarget,
)

__all__ = ["BaseAdapter", "MessageEvent", "MessageHandler", "MessageType", "PushTarget"]
