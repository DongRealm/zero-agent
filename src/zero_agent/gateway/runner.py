import asyncio
import time
from collections.abc import Coroutine
from typing import Any

from zero_agent.gateway.protocol import BaseAdapter, MessageEvent
from zero_agent.runner.dispatcher import MessageDispatcher


class GateRunner:
    def __init__(self) -> None:
        self.adapters: dict[str, BaseAdapter] = {}
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._drain_timeout = 10
        self._running_agents: dict[str, asyncio.Task[None]] = {}
        self._failed_platforms: dict[str, dict[str, Any]] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._dispatcher = MessageDispatcher()

    async def start(self) -> bool:
        for name, adapter in self.adapters.items():
            try:
                success = await adapter.connect()
                if success:
                    print(f"{name} connected")
                else:
                    self._failed_platforms[name] = {
                        "adapter": adapter,
                        "attempts": 0,
                        "next_retry": time.monotonic() + 30,
                    }
            except Exception as e:
                print(f"Failed to connect to {name}: {e}")
                self._failed_platforms[name] = {
                    "adapter": adapter,
                    "attempts": 0,
                    "next_retry": time.monotonic() + 30,
                }

        self._running = True

        self._start_background_task(self._session_expiry_watcher())
        self._start_background_task(self._platform_reconnect_watcher())

        print(f"运行中，已连接 {len(self.adapters) - len(self._failed_platforms)} 个平台")
        return True

    async def stop(self) -> None:
        self._running = False
        print(f"Drain: 等待{len(self._running_agents)} 个活跃 Agent 完成处理...")
        deadline = time.monotonic() + self._drain_timeout
        while self._running_agents and time.monotonic() < deadline:
            await asyncio.sleep(0.1)

        if self._running_agents:
            print(f"Drain 超时: 仍然有 {len(self._running_agents)} 个活跃 Agent 未完成处理")
            for task in self._running_agents.values():
                task.cancel()
            await asyncio.sleep(0.5)

        for adapter in self.adapters.values():
            await adapter.disconnect()

        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

        self._shutdown_event.set()
        print("已停止")

    async def await_for_shutdown(self) -> None:
        await self._shutdown_event.wait()

    async def handle_message(self, event: MessageEvent) -> str | None:
        return await self._dispatcher.handle(event)

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
                print(f"{name} 尝试重新连接...")

                try:
                    success = await adapter.connect()
                    if success:
                        print(f"{name} 重连成功")
                        del self._failed_platforms[name]
                    else:
                        backoff = min(30 * (2 ** info["attempts"]), backoff_cap)
                        info["next_retry"] = now + backoff
                except Exception as e:
                    backoff = min(30 * (2 ** info["attempts"]), backoff_cap)
                    info["next_retry"] = now + backoff
                    print(f"{name} 重连失败: {e}")

            await asyncio.sleep(5)
