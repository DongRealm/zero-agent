"""Register enabled gateway adapters from settings."""

from __future__ import annotations

from zero_agent.gateway.protocol import BaseAdapter
from zero_agent.settings import Settings


def build_adapters(settings: Settings) -> dict[str, BaseAdapter]:
    """Build enabled platform adapters. Wired in Phase F step 24."""
    _ = settings
    return {}
