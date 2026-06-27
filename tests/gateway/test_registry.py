from pydantic import SecretStr

from zero_agent.gateway.platforms.wecom import WecomAdapter
from zero_agent.gateway.registry import build_adapters
from zero_agent.settings import Settings


def test_build_adapters_empty_when_wecom_disabled() -> None:
    settings = Settings(wecom_bot_secret=SecretStr(""))

    assert build_adapters(settings) == {}


def test_build_adapters_includes_wecom_when_configured() -> None:
    settings = Settings(
        wecom_bot_id="bot-1",
        wecom_bot_secret=SecretStr("secret"),
    )

    adapters = build_adapters(settings)

    assert set(adapters) == {"wecom"}
    assert isinstance(adapters["wecom"], WecomAdapter)
