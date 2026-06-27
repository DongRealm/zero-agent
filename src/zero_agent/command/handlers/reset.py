"""Reset conversation thread (/reset, /new, etc.)."""

from __future__ import annotations

from zero_agent.command.base import CommandContext, CommandResult
from zero_agent.i18n import I18n
from zero_agent.session.registry import SessionRegistry

RESET_NAMES = frozenset({"/reset", "/new", "重置", "新对话"})


class ResetCommand:
    names = RESET_NAMES

    def __init__(self, registry: SessionRegistry, i18n: I18n | None = None) -> None:
        self._registry = registry
        self._i18n = i18n or I18n()

    async def run(self, ctx: CommandContext) -> CommandResult:
        await self._registry.reset(ctx.key)
        message = self._i18n.t("command.reset.done", ctx.locale)
        return CommandResult(message=message)
