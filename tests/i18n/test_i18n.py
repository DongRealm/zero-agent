import pytest

from zero_agent.i18n import DEFAULT_LOCALE, I18n, normalize_locale


@pytest.fixture
def i18n() -> I18n:
    return I18n()


def test_t_zh_reset_done(i18n: I18n) -> None:
    assert i18n.t("command.reset.done", "zh") == "已开启新对话，上下文已清空。"


def test_t_en_reset_done(i18n: I18n) -> None:
    assert i18n.t("command.reset.done", "en") == "New conversation started. Context cleared."


def test_t_en_lang_invalid(i18n: I18n) -> None:
    assert i18n.t("command.lang.invalid", "en") == "Usage: /lang zh or /lang en"


def test_normalize_locale_tags() -> None:
    assert normalize_locale("zh_CN") == "zh"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("fr") == DEFAULT_LOCALE


def test_t_falls_back_to_default_locale(i18n: I18n) -> None:
    custom = I18n(
        locales={
            "zh": {"only": {"zh": "中文"}},
            "en": {},
        }
    )
    assert custom.t("only.zh", "en") == "中文"


def test_t_returns_key_when_missing(i18n: I18n) -> None:
    assert i18n.t("missing.key", "zh") == "missing.key"
    assert i18n.t("missing.key", "en") == "missing.key"


def test_t_supports_format_kwargs() -> None:
    custom = I18n(locales={"zh": {"greet": {"hello": "你好，{name}！"}}})
    assert custom.t("greet.hello", "zh", name="Zero") == "你好，Zero！"
