"""Switch session UI locale (/lang, /语言)."""

from __future__ import annotations

from zero_agent.command.base import CommandContext, CommandResult
from zero_agent.i18n import SUPPORTED_LOCALES, I18n
from zero_agent.session.registry import SessionRegistry

LANG_NAMES = frozenset({"/lang", "/语言"})

_ZH_ALIASES = frozenset({"zh", "中文"})
_EN_ALIASES = frozenset({"en", "英文", "english"})


def parse_lang_arg(raw: str) -> str | None:
    """Map user input to a supported locale code."""
    token = raw.strip()
    lowered = token.lower()
    if lowered in _ZH_ALIASES or token in _ZH_ALIASES:
        return "zh"
    if lowered in _EN_ALIASES or token in _EN_ALIASES:
        return "en"
    if lowered in SUPPORTED_LOCALES:
        return lowered
    return None


class LangCommand:
    names = LANG_NAMES
    description_key = "command.lang.description"

    def __init__(self, registry: SessionRegistry, i18n: I18n | None = None) -> None:
        self._registry = registry
        self._i18n = i18n or I18n()

    async def run(self, ctx: CommandContext) -> CommandResult:
        if len(ctx.args) != 1:
            return CommandResult(message=self._i18n.t("command.lang.invalid", ctx.locale))

        target = parse_lang_arg(ctx.args[0])
        if target is None:
            return CommandResult(message=self._i18n.t("command.lang.invalid", ctx.locale))

        await self._registry.set_locale(ctx.key, target)
        message = self._i18n.t("command.lang.done", target)
        return CommandResult(message=message)
