"""Application runner: wiring lifecycle, gateway adapters, and dispatch."""

from __future__ import annotations

import asyncio

from zero_agent.agent import AgentService
from zero_agent.command import CommandRouter, HelpCommand, LangCommand, ResetCommand
from zero_agent.gateway.protocol import BaseAdapter
from zero_agent.gateway.registry import build_adapters
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
from zero_agent.session.checkpoint import CheckpointStore
from zero_agent.session.registry import SessionRegistry
from zero_agent.settings import Settings
from zero_agent.settings import settings as default_settings


def wire_gate_runner(
    registry: SessionRegistry,
    commands: CommandRouter,
    agent: AgentService,
    adapters: dict[str, BaseAdapter],
) -> GateRunner:
    """Wire registry, commands, agent, and adapters into a GateRunner."""
    dispatcher = MessageDispatcher(registry, commands, agent)
    runner = GateRunner(dispatcher)
    for name, adapter in adapters.items():
        adapter.set_message_handler(runner.handle_message)
        runner.adapters[name] = adapter
    return runner


class ApplicationRunner:
    """Orchestrates process lifecycle and gateway adapters."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or default_settings
        self._registry = SessionRegistry(
            self._settings.resolved_session_db_path,
            default_locale=self._settings.default_locale,
            checkpoint_db_path=self._settings.resolved_checkpoint_db_path,
        )
        self._commands = CommandRouter(
            [
                ResetCommand(self._registry),
                LangCommand(self._registry),
            ]
        )
        self._commands.register(HelpCommand(self._commands))
        self._cron = CronRunner(
            interval=60,
            on_tick=session_expire_tick(self._registry, self._settings.session_ttl_seconds),
        )
        self._runner: GateRunner | None = None
        self._checkpoint: CheckpointStore | None = None

    @property
    def runner(self) -> GateRunner:
        if self._runner is None:
            raise RuntimeError("ApplicationRunner is not running")
        return self._runner

    async def run(self) -> bool:
        if not acquire_pid_file():
            return False

        await self._registry.open()
        self._checkpoint = CheckpointStore(self._settings.resolved_checkpoint_db_path)
        await self._checkpoint.__aenter__()
        try:
            agent = AgentService.from_settings(
                self._settings,
                checkpointer=self._checkpoint.saver,
            )
            self._runner = wire_gate_runner(
                self._registry,
                self._commands,
                agent,
                build_adapters(self._settings),
            )

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
            if self._checkpoint is not None:
                await self._checkpoint.__aexit__(None, None, None)
                self._checkpoint = None
            self._runner = None
            await self._registry.close()
            release_pid_file()


async def run_application() -> bool:
    app = ApplicationRunner()
    return await app.run()
