"""Inbound message routing: Command branch first, Agent branch in step 23."""

from __future__ import annotations

from zero_agent.command.base import CommandContext
from zero_agent.command.router import CommandRouter
from zero_agent.gateway.outbound import OutboundChannel
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry


class MessageDispatcher:
    """Routes inbound messages to Command handlers or Agent (mock echo until step 23)."""

    def __init__(
        self,
        registry: SessionRegistry,
        commands: CommandRouter,
    ) -> None:
        self._registry = registry
        self._commands = commands

    async def handle(
        self,
        event: MessageEvent,
        outbound: OutboundChannel | None = None,
    ) -> str | None:
        """Process one inbound message.

        Commands reply via ``outbound`` when provided; otherwise return reply text
        for the transitional handler return path. Non-commands still echo.
        """
        key = SessionKey.from_event(event)
        locale = await self._registry.get_locale(key)

        matched = self._commands.match(event.content)
        if matched is not None:
            ctx = CommandContext(key=key, locale=locale, event=event, args=[])
            result = await self._commands.dispatch(matched, ctx)
            if outbound is not None:
                await outbound.reply(event, result.message)
                return None
            return result.message

        return f"已收到消息: {event.content}"
