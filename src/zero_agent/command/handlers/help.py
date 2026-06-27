"""List available local commands (/help, 帮助)."""

from __future__ import annotations

from zero_agent.command.base import CommandContext, CommandResult
from zero_agent.command.router import CommandRouter
from zero_agent.i18n import I18n

HELP_NAMES = frozenset({"/help", "帮助"})


def format_command_triggers(names: frozenset[str]) -> str:
    """Format trigger names for help output (/commands first)."""
    slash = sorted(name for name in names if name.startswith("/"))
    other = sorted(name for name in names if not name.startswith("/"))
    return "、".join(slash + other)


def build_help_message(router: CommandRouter, i18n: I18n, locale: str) -> str:
    """Build help text from registered handlers and per-command i18n keys."""
    lines = [i18n.t("command.help.header", locale)]
    for handler in router.handlers:
        triggers = format_command_triggers(handler.names)
        description = i18n.t(handler.description_key, locale)
        lines.append(f"· {triggers} — {description}")
    return "\n".join(lines)


class HelpCommand:
    names = HELP_NAMES
    description_key = "command.help.description"

    def __init__(self, router: CommandRouter, i18n: I18n | None = None) -> None:
        self._router = router
        self._i18n = i18n or I18n()

    async def run(self, ctx: CommandContext) -> CommandResult:
        message = build_help_message(self._router, self._i18n, ctx.locale)
        return CommandResult(message=message)
