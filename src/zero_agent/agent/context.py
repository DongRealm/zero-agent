"""Runtime context passed to Deep Agents on each invoke."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentContext:
    """Per-run context for memory namespace scoping."""

    user_id: str
