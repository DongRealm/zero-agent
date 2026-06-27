"""Inbound message routing: Command branch first, then Agent."""

from __future__ import annotations

from zero_agent.agent.service import AgentService
from zero_agent.agent.types import AgentError
from zero_agent.command.base import CommandContext
from zero_agent.command.router import CommandRouter
from zero_agent.gateway.outbound import OutboundChannel
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.i18n import I18n
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
        locale = await self._registry.get_locale(key)

        matched = self._commands.match(event.content)
        if matched is not None:
            ctx = CommandContext(key=key, locale=locale, event=event, args=[])
            result = await self._commands.dispatch(matched, ctx)
            await self._reply(outbound, event, result.message)
            return

        thread_id = await self._registry.resolve_thread_id(key)
        try:
            result = await self._agent.invoke(thread_id, event.content)
        except AgentError:
            logger.exception("agent.invoke_failed", thread_id=thread_id, session_id=event.session_id)
            await self._reply(outbound, event, self._i18n.t("error.agent_failed", locale))
            return
        except Exception:
            logger.exception("agent.invoke_failed", thread_id=thread_id, session_id=event.session_id)
            await self._reply(outbound, event, self._i18n.t("error.agent_failed", locale))
            return

        await self._reply(outbound, event, result.content)

    async def _reply(
        self,
        outbound: OutboundChannel | None,
        event: MessageEvent,
        content: str,
    ) -> None:
        if outbound is None:
            logger.warning("dispatcher.no_outbound", session_id=event.session_id or None)
            return
        await outbound.reply(event, content)
