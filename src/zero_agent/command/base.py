"""Command handler types and context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from zero_agent.gateway.protocol import MessageEvent
from zero_agent.session.models import SessionKey


@dataclass(frozen=True)
class CommandContext:
    key: SessionKey
    locale: str
    event: MessageEvent
    args: list[str]


@dataclass(frozen=True)
class CommandResult:
    message: str


@runtime_checkable
class CommandHandler(Protocol):
    names: frozenset[str]
    description_key: str

    async def run(self, ctx: CommandContext) -> CommandResult: ...
