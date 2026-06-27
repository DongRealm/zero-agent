from __future__ import annotations

from typing import Any

from aibot import WSClient, WSClientOptions
from pydantic import SecretStr

from zero_agent.gateway.base_adapter import BaseAdapter, MessageEvent, MessageType


class WecomAdapter(BaseAdapter):
    def __init__(self, bot_id: str, secret: SecretStr) -> None:
        options = WSClientOptions(
            bot_id=bot_id,
            secret=secret.get_secret_value(),
        )
        self._client = WSClient(options)
        self._register_handlers()

    async def connect(self) -> bool:
        await self._client.connect()
        return True

    async def disconnect(self) -> None:
        self._client.disconnect()

    def _register_handlers(self) -> None:
        self._client.on("authenticated")(self._on_authenticated)
        self._client.on("message.text")(self._on_text)

    def _on_authenticated(self) -> None:
        print(f"[{self.name}] 认证成功")

    async def _on_text(self, frame: dict[str, Any]) -> None:
        """监听文本消息"""
        body = frame.get("body", {})
        print(f"[{self.name}] 收到消息: {body}")
        event = MessageEvent(
            platform=self.name,
            content=body.get("text", {}).get("content", ""),
            msg_type=MessageType.TEXT,
            extra=frame,
        )
        await self.handle_message(event)

    async def _send_reply(self, event: MessageEvent, reply: str) -> None:
        """Send a reply through WeCom."""
        frame = event.extra or {}
        await self._client.reply(frame, {"msgtype": "markdown", "markdown": {"content": reply}})
