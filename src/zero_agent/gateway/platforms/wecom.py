from __future__ import annotations

from typing import Any

from aibot import WSClient, WSClientOptions
from pydantic import SecretStr

from zero_agent.gateway.outbound import (
    AdapterCapabilities,
    ApprovalRequest,
    OutboundChannel,
    UnsupportedOutboundError,
)
from zero_agent.gateway.protocol import BaseAdapter, MessageEvent, MessageType, PushTarget
from zero_agent.observability.setup import get_logger
from zero_agent.session.models import SessionKey

logger = get_logger(__name__)


def parse_wecom_session_id(frame: dict[str, Any]) -> str:
    """Build session_id from WeCom callback frame."""
    return wecom_session_key_from_frame(frame).to_id()


def wecom_session_key_from_frame(frame: dict[str, Any]) -> SessionKey:
    body = frame.get("body") or {}
    chat_id = _first_str(body, "chatid", "chat_id") or _first_str(frame, "chatid", "chat_id")
    user_id = _first_str(body, "userid", "user_id") or _first_str(frame, "userid", "user_id")
    return SessionKey(platform="wecom", chat_id=chat_id, user_id=user_id or None)


def parse_wecom_push_target(frame: dict[str, Any]) -> PushTarget:
    """Extract proactive push target from a WeCom callback frame."""
    body = frame.get("body") or {}
    chat_id = _first_str(body, "chatid", "chat_id") or _first_str(frame, "chatid", "chat_id")
    chat_type = _first_int(body, "chattype", "chat_type")
    if chat_type is None:
        chat_type = _first_int(frame, "chattype", "chat_type")
    return PushTarget(chat_id=chat_id, chat_type=chat_type)


def message_event_from_frame(frame: dict[str, Any]) -> MessageEvent:
    """Normalize a WeCom text callback frame into MessageEvent."""
    body = frame.get("body") or {}
    text = body.get("text", {})
    content = text.get("content", "") if isinstance(text, dict) else ""
    if not isinstance(content, str):
        content = str(content)

    key = wecom_session_key_from_frame(frame)
    return MessageEvent(
        platform="wecom",
        session_id=key.to_id(),
        content=content,
        msg_type=MessageType.TEXT,
        push_target=parse_wecom_push_target(frame),
        reply_to=frame,
        extra=frame,
    )


def _first_str(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _first_int(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


class WecomAdapter(BaseAdapter, OutboundChannel):
    capabilities = AdapterCapabilities(reply=True, reply_stream=True)

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
        event = message_event_from_frame(frame)
        logger.info(
            "message.received",
            platform=self.name,
            session_id=event.session_id,
            content_len=len(event.content),
        )
        await self.handle_message(event)

    async def reply(self, event: MessageEvent, content: str) -> None:
        frame = event.reply_to or event.extra or {}
        await self._client.reply(
            frame,
            {"msgtype": "markdown", "markdown": {"content": content}},
        )

    async def reply_stream(
        self,
        event: MessageEvent,
        stream_id: str,
        content: str,
        *,
        finish: bool = False,
    ) -> None:
        frame = event.reply_to or event.extra or {}
        await self._client.reply_stream(frame, stream_id, content, finish)

    async def push(self, target: PushTarget, content: str) -> None:
        del target, content
        raise UnsupportedOutboundError("WeCom push not implemented yet")

    async def request_approval(self, event: MessageEvent, req: ApprovalRequest) -> None:
        del event, req
        raise UnsupportedOutboundError("WeCom approval_card not implemented yet")

    async def update_approval(self, event: MessageEvent, req: ApprovalRequest) -> None:
        del event, req
        raise UnsupportedOutboundError("WeCom approval_card_update not implemented yet")

    async def _send_reply(self, event: MessageEvent, reply: str) -> None:
        await self.reply(event, reply)
