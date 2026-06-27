"""Inbound message routing: Command branch first, then Agent."""

from __future__ import annotations

import time

from zero_agent.agent.service import AgentService
from zero_agent.agent.types import AgentError
from zero_agent.command.base import CommandContext
from zero_agent.command.router import CommandRouter
from zero_agent.gateway.outbound import OutboundChannel
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.i18n import I18n
from zero_agent.observability.context import bind_thread_id, message_context
from zero_agent.observability.setup import get_logger
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry

logger = get_logger(__name__)


class MessageDispatcher:
    """Routes inbound messages to Command handlers or AgentService."""

    def __init__(
        self,
        registry: SessionRegistry,
        commands: CommandRouter,
        agent: AgentService,
        i18n: I18n | None = None,
    ) -> None:
        self._registry = registry
        self._commands = commands
        self._agent = agent
        self._i18n = i18n or I18n()

    async def handle(self, event: MessageEvent, outbound: OutboundChannel | None = None) -> None:
        """Process one inbound message and send replies via ``outbound``."""
        key = SessionKey.from_event(event)
        session_key = key.to_id()
        locale = await self._registry.get_locale(key)

        with message_context(session_key=session_key):
            started = time.monotonic()
            logger.info("dispatch.start", platform=event.platform)

            matched = self._commands.match(event.content)
            if matched is not None:
                ctx = CommandContext(key=key, locale=locale, event=event, args=[])
                result = await self._commands.dispatch(matched, ctx)
                await self._reply(outbound, event, result.message)
                logger.info("dispatch.end", duration_ms=_duration_ms(started), route="command")
                return

            thread_id = await self._registry.resolve_thread_id(key)
            bind_thread_id(thread_id)
            try:
                result = await self._agent.invoke(thread_id, event.content)
            except AgentError:
                logger.exception("agent.invoke_failed", duration_ms=_duration_ms(started))
                await self._reply(outbound, event, self._i18n.t("error.agent_failed", locale))
                logger.info("dispatch.end", duration_ms=_duration_ms(started), route="agent", ok=False)
                return
            except Exception:
                logger.exception("agent.invoke_failed", duration_ms=_duration_ms(started))
                await self._reply(outbound, event, self._i18n.t("error.agent_failed", locale))
                logger.info("dispatch.end", duration_ms=_duration_ms(started), route="agent", ok=False)
                return

            await self._reply(outbound, event, result.content)
            logger.info("dispatch.end", duration_ms=_duration_ms(started), route="agent", ok=True)

    async def _reply(
        self,
        outbound: OutboundChannel | None,
        event: MessageEvent,
        content: str,
    ) -> None:
        if outbound is None:
            logger.warning("dispatcher.no_outbound")
            return
        await outbound.reply(event, content)


def _duration_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
