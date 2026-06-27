"""Load and resolve localized system UI strings."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml

SUPPORTED_LOCALES = ("zh", "en")
DEFAULT_LOCALE = "zh"


class I18n:
    """Resolve dotted message keys from locale YAML files."""

    def __init__(self, locales: dict[str, dict[str, Any]] | None = None) -> None:
        if locales is None:
            locales = {locale: _load_locale_file(locale) for locale in SUPPORTED_LOCALES}
        self._locales = locales

    def t(self, key: str, locale: str, **kwargs: object) -> str:
        """Return localized text for ``key``, with optional ``str.format`` kwargs."""
        normalized = normalize_locale(locale)
        text = self._lookup(key, normalized)
        if text is None and normalized != DEFAULT_LOCALE:
            text = self._lookup(key, DEFAULT_LOCALE)
        if text is None:
            return key
        if kwargs:
            return text.format(**kwargs)
        return text

    def _lookup(self, key: str, locale: str) -> str | None:
        node: object = self._locales.get(locale, {})
        for part in key.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return node if isinstance(node, str) else None


def normalize_locale(locale: str) -> str:
    """Map locale tags like ``zh_CN`` / ``en-US`` to supported MVP codes."""
    base = locale.replace("-", "_").split("_", 1)[0].lower()
    if base in SUPPORTED_LOCALES:
        return base
    return DEFAULT_LOCALE


def _load_locale_file(locale: str) -> dict[str, Any]:
    path = files("zero_agent.i18n.locales").joinpath(f"{locale}.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}
