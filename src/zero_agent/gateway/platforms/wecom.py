from __future__ import annotations

from typing import Any

from aibot import WSClient, WSClientOptions
from pydantic import SecretStr

from zero_agent.gateway.protocol import BaseAdapter, MessageEvent, MessageType
from zero_agent.observability.setup import get_logger
from zero_agent.session.models import SessionKey

logger = get_logger(__name__)


def parse_wecom_session_id(frame: dict[str, Any]) -> str:
    """Build interim session_id from WeCom callback frame."""
    return wecom_session_key_from_frame(frame).to_id()


def wecom_session_key_from_frame(frame: dict[str, Any]) -> SessionKey:
    body = frame.get("body") or {}
    chat_id = _first_str(body, "chatid", "chat_id") or _first_str(frame, "chatid", "chat_id")
    user_id = _first_str(body, "userid", "user_id") or _first_str(frame, "userid", "user_id")
    return SessionKey(platform="wecom", chat_id=chat_id, user_id=user_id or None)


def _first_str(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


class WecomAdapter(BaseAdapter):
    def __init__(self, bot_id: str, secret: SecretStr) -> None:
        super().__init__(name="wecom")
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
        logger.info("adapter.authenticated", platform=self.name)

    async def _on_text(self, frame: dict[str, Any]) -> None:
        body = frame.get("body", {})
        content = body.get("text", {}).get("content", "")
        session_id = parse_wecom_session_id(frame)
        logger.info(
            "message.received",
            platform=self.name,
            session_id=session_id,
            content_len=len(content),
        )
        event = MessageEvent(
            platform=self.name,
            session_id=session_id,
            content=content,
            msg_type=MessageType.TEXT,
            extra=frame,
        )
        await self.handle_message(event)

    async def _send_reply(self, event: MessageEvent, reply: str) -> None:
        frame = event.extra or {}
        await self._client.reply(frame, {"msgtype": "markdown", "markdown": {"content": reply}})
