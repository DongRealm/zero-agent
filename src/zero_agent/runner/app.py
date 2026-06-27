"""Application runner: wiring lifecycle, gateway adapters, and dispatch."""

from __future__ import annotations

import asyncio

from zero_agent.agent import AgentService
from zero_agent.command import CommandRouter, LangCommand, ResetCommand
from zero_agent.gateway.platforms.wecom import WecomAdapter
from zero_agent.gateway.runner import GateRunner
from zero_agent.runner.dispatcher import MessageDispatcher
from zero_agent.runner.lifecycle import (
    CronRunner,
    acquire_pid_file,
    install_exception_handler,
    register_signal_handlers,
    release_pid_file,
    session_expire_tick,
)
from zero_agent.session.registry import SessionRegistry
from zero_agent.settings import settings


def wecom_enabled() -> bool:
    return bool(settings.wecom_bot_id and settings.wecom_bot_secret.get_secret_value())


class ApplicationRunner:
    """Orchestrates process lifecycle and gateway adapters."""

    def __init__(self) -> None:
        self._registry = SessionRegistry(
            settings.resolved_session_db_path,
            default_locale=settings.default_locale,
            checkpoint_db_path=settings.resolved_checkpoint_db_path,
        )
        self._commands = CommandRouter(
            [
                ResetCommand(self._registry),
                LangCommand(self._registry),
            ]
        )
        self._agent = AgentService.from_settings(settings)
        self._dispatcher = MessageDispatcher(
            self._registry,
            self._commands,
            self._agent,
        )
        self._runner = GateRunner(self._dispatcher)
        self._cron = CronRunner(
            interval=60,
            on_tick=session_expire_tick(self._registry, settings.session_ttl_seconds),
        )

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

        await self._registry.open()
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
            await self._registry.close()
            release_pid_file()


async def run_application() -> bool:
    app = ApplicationRunner()
    return await app.run()
