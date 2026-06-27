"""Application runner: wiring lifecycle, gateway adapters, and dispatch."""

from __future__ import annotations

import asyncio

from zero_agent.gateway.platforms.wecom import WecomAdapter
from zero_agent.gateway.runner import GateRunner
from zero_agent.runner.lifecycle import (
    CronRunner,
    acquire_pid_file,
    install_exception_handler,
    register_signal_handlers,
    release_pid_file,
)
from zero_agent.settings import settings


def wecom_enabled() -> bool:
    return bool(settings.wecom_bot_id and settings.wecom_bot_secret.get_secret_value())


class ApplicationRunner:
    """Orchestrates process lifecycle and gateway adapters."""

    def __init__(self) -> None:
        self._runner = GateRunner()
        self._cron = CronRunner(interval=60)

    @property
    def runner(self) -> GateRunner:
        return self._runner

    def _register_adapters(self) -> None:
        if not wecom_enabled():
            return
        bot_id = settings.wecom_bot_id
        assert bot_id is not None
        wecom_adapter = WecomAdapter(
            bot_id=bot_id,
            secret=settings.wecom_bot_secret,
        )
        wecom_adapter.set_message_handler(self._runner.handle_message)
        self._runner.adapters["wecom"] = wecom_adapter

    async def run(self) -> bool:
        if not acquire_pid_file():
            return False

        try:
            self._register_adapters()

            loop = asyncio.get_running_loop()
            register_signal_handlers(loop, self._runner.stop)
            install_exception_handler(loop)

            success = await self._runner.start()
            if not success:
                return False

            self._cron.start()
            await self._runner.await_for_shutdown()
            self._cron.stop()
            return True
        finally:
            release_pid_file()


async def run_application() -> bool:
    app = ApplicationRunner()
    return await app.run()
