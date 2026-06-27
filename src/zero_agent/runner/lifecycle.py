"""Process lifecycle: PID file, signal handlers, and cron ticker."""

from __future__ import annotations

import asyncio
import os
import signal
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from pathlib import Path
from typing import Any

from zero_agent.session.registry import SessionRegistry
from zero_agent.settings import settings


def pid_file_path() -> Path:
    return Path(settings.data_dir, "gateway.pid")


def acquire_pid_file() -> bool:
    """Claim the PID file. Returns False if another instance is already running."""
    pid_file = pid_file_path()
    if pid_file.exists():
        old_pid = int(pid_file.read_text().strip())
        try:
            os.kill(old_pid, 0)
            print(f"Gateway is already running with PID {old_pid}. Exiting.")
            return False
        except ProcessLookupError:
            pid_file.unlink()
    pid_file.write_text(str(os.getpid()))
    return True


def release_pid_file() -> None:
    pid_file_path().unlink(missing_ok=True)


def register_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    on_shutdown: Callable[[], Coroutine[Any, Any, None]],
) -> None:
    def shutdown_handler(sig: signal.Signals) -> None:
        print(f"Received signal {sig}. Shutting down...")
        asyncio.create_task(on_shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler, sig)


def install_exception_handler(loop: asyncio.AbstractEventLoop) -> None:
    def exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, object]) -> None:
        exc = context.get("exception")
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            print(f"吞吐瞬时网络错误：{exc}")
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(exception_handler)


def _schedule_tick_callback(
    loop: asyncio.AbstractEventLoop,
    on_tick: Callable[[], Coroutine[Any, Any, None]],
) -> None:
    future = asyncio.run_coroutine_threadsafe(on_tick(), loop)

    def _log_failure(done: Future[None]) -> None:
        try:
            done.result()
        except Exception as exc:
            print(f"Cron tick callback failed: {exc}")

    future.add_done_callback(_log_failure)


def cron_ticker(
    stop_event: threading.Event,
    loop: asyncio.AbstractEventLoop,
    interval: int = 60,
    on_tick: Callable[[], Coroutine[Any, Any, None]] | None = None,
) -> None:
    print(f"Cron ticker started. Interval: {interval}s")
    tick_count = 0
    while not stop_event.is_set():
        if on_tick is not None:
            _schedule_tick_callback(loop, on_tick)
        print(f"Cron tick {tick_count}")
        tick_count += 1
        stop_event.wait(timeout=interval)
    print("Cron ticker stopped")


class CronRunner:
    """Background cron thread tied to the asyncio event loop."""

    def __init__(
        self,
        interval: int = 60,
        on_tick: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._interval = interval
        self._on_tick = on_tick
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._thread = threading.Thread(
            target=cron_ticker,
            args=(self._stop, loop),
            kwargs={"interval": self._interval, "on_tick": self._on_tick},
            daemon=True,
            name="CronTicker",
        )
        self._thread.start()

    def stop(self, timeout: float = 5) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)


def session_expire_tick(
    registry: SessionRegistry,
    ttl_seconds: int,
) -> Callable[[], Coroutine[Any, Any, None]]:
    """Build a cron callback that purges expired closed session threads."""

    async def on_tick() -> None:
        purged = await registry.expire_stale(ttl_seconds=ttl_seconds)
        if purged:
            print(f"Session maintenance: purged {len(purged)} closed thread(s)")

    return on_tick
