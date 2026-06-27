"""Match and dispatch local slash commands."""

from __future__ import annotations

import re
from dataclasses import dataclass

from zero_agent.command.base import CommandContext, CommandHandler, CommandResult

_AT_PREFIX = re.compile(r"^@\S+\s*")


@dataclass(frozen=True)
class MatchedCommand:
    handler: CommandHandler
    trigger: str
    args: list[str]


def normalize_command_text(text: str) -> str:
    """Strip whitespace and optional @bot mention prefix."""
    normalized = text.strip()
    normalized = _AT_PREFIX.sub("", normalized, count=1).strip()
    return normalized


class CommandRouter:
    def __init__(self, handlers: list[CommandHandler] | None = None) -> None:
        self._handlers: list[CommandHandler] = list(handlers or [])
        self._names: list[tuple[str, CommandHandler]] = []
        self._rebuild_index()

    def register(self, handler: CommandHandler) -> None:
        self._handlers.append(handler)
        self._rebuild_index()

    def match(self, text: str) -> MatchedCommand | None:
        normalized = normalize_command_text(text)
        if not normalized:
            return None

        for name, handler in self._names:
            if normalized == name:
                return MatchedCommand(handler=handler, trigger=name, args=[])
            prefix = f"{name} "
            if normalized.startswith(prefix):
                arg_text = normalized[len(prefix) :].strip()
                args = arg_text.split() if arg_text else []
                return MatchedCommand(handler=handler, trigger=name, args=args)

        return None

    async def dispatch(self, matched: MatchedCommand, ctx: CommandContext) -> CommandResult:
        dispatch_ctx = CommandContext(
            key=ctx.key,
            locale=ctx.locale,
            event=ctx.event,
            args=list(matched.args),
        )
        return await matched.handler.run(dispatch_ctx)

    @property
    def handlers(self) -> list[CommandHandler]:
        return list(self._handlers)

    def _rebuild_index(self) -> None:
        pairs: list[tuple[str, CommandHandler]] = []
        for handler in self._handlers:
            for name in handler.names:
                pairs.append((name, handler))
        self._names = sorted(pairs, key=lambda item: len(item[0]), reverse=True)
