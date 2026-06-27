"""Register enabled gateway adapters from settings."""

from __future__ import annotations

from zero_agent.gateway.platforms.wecom import WecomAdapter
from zero_agent.gateway.protocol import BaseAdapter
from zero_agent.settings import Settings


def build_adapters(settings: Settings) -> dict[str, BaseAdapter]:
    """Build enabled platform adapters from settings."""
    adapters: dict[str, BaseAdapter] = {}

    if settings.wecom_bot_id and settings.wecom_bot_secret.get_secret_value():
        adapters["wecom"] = WecomAdapter(
            bot_id=settings.wecom_bot_id,
            secret=settings.wecom_bot_secret,
        )

    return adapters
