import asyncio
import time
from collections.abc import Coroutine
from typing import Any

from zero_agent.gateway.outbound import OutboundChannel
from zero_agent.gateway.protocol import BaseAdapter, MessageEvent
from zero_agent.observability.setup import get_logger
from zero_agent.runner.dispatcher import MessageDispatcher

logger = get_logger(__name__)


class GateRunner:
    def __init__(self, dispatcher: MessageDispatcher) -> None:
        self.adapters: dict[str, BaseAdapter] = {}
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._drain_timeout = 10
        self._running_agents: dict[str, asyncio.Task[None]] = {}
        self._failed_platforms: dict[str, dict[str, Any]] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._dispatcher = dispatcher

    async def start(self) -> bool:
        for name, adapter in self.adapters.items():
            try:
                success = await adapter.connect()
                if success:
                    logger.info("adapter.connect", platform=name)
                else:
                    self._failed_platforms[name] = {
                        "adapter": adapter,
                        "attempts": 0,
                        "next_retry": time.monotonic() + 30,
                    }
            except Exception:
                logger.exception("adapter.connect_failed", platform=name)
                self._failed_platforms[name] = {
                    "adapter": adapter,
                    "attempts": 0,
                    "next_retry": time.monotonic() + 30,
                }

        self._running = True

        self._start_background_task(self._session_expiry_watcher())
        self._start_background_task(self._platform_reconnect_watcher())

        connected = len(self.adapters) - len(self._failed_platforms)
        logger.info("gateway.start", connected_platforms=connected)
        return True

    async def stop(self) -> None:
        self._running = False
        active = len(self._running_agents)
        logger.info("gateway.drain_start", count=active)
        deadline = time.monotonic() + self._drain_timeout
        while self._running_agents and time.monotonic() < deadline:
            await asyncio.sleep(0.1)

        if self._running_agents:
            remaining = len(self._running_agents)
            logger.warning("gateway.drain_timeout", count=remaining)
            for task in self._running_agents.values():
                task.cancel()
            await asyncio.sleep(0.5)

        for adapter in self.adapters.values():
            await adapter.disconnect()

        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

        self._shutdown_event.set()
        logger.info("gateway.stop")

    async def await_for_shutdown(self) -> None:
        await self._shutdown_event.wait()

    async def handle_message(self, event: MessageEvent) -> None:
        outbound = self._outbound_for(event)
        await self._dispatcher.handle(event, outbound)

    def _outbound_for(self, event: MessageEvent) -> OutboundChannel | None:
        adapter = self.adapters.get(event.platform)
        if adapter is not None and hasattr(adapter, "reply"):
            return adapter  # type: ignore[return-value]
        return None

    def _start_background_task(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _session_expiry_watcher(self, interval: int = 60) -> None:
        await asyncio.sleep(5)
        while self._running:
            # 真实场景：遍历SessionStore，清理过期回话
            await asyncio.sleep(interval)

    async def _platform_reconnect_watcher(self) -> None:
        backoff_cap = 300
        await asyncio.sleep(10)
        while self._running:
            if not self._failed_platforms:
                await asyncio.sleep(30)
                continue

            now = time.monotonic()
            for name in list(self._failed_platforms.keys()):
                info = self._failed_platforms[name]
                if now < info["next_retry"]:
                    continue

                info["attempts"] += 1
                adapter = info["adapter"]
                attempt = info["attempts"]
                logger.info("adapter.reconnect", platform=name, attempt=attempt)

                try:
                    success = await adapter.connect()
                    if success:
                        logger.info("adapter.reconnect_ok", platform=name)
                        del self._failed_platforms[name]
                    else:
                        backoff = min(30 * (2 ** info["attempts"]), backoff_cap)
                        info["next_retry"] = now + backoff
                except Exception:
                    backoff = min(30 * (2 ** info["attempts"]), backoff_cap)
                    info["next_retry"] = now + backoff
                    logger.exception("adapter.reconnect_failed", platform=name, attempt=attempt)

            await asyncio.sleep(5)
