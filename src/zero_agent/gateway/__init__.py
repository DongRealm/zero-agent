from zero_agent.gateway.inbound import InboundKind
from zero_agent.gateway.outbound import AdapterCapabilities, OutboundChannel
from zero_agent.gateway.platforms.wecom import WecomAdapter
from zero_agent.gateway.protocol import BaseAdapter, MessageEvent, MessageHandler, MessageType
from zero_agent.gateway.registry import build_adapters

__all__ = [
    "AdapterCapabilities",
    "BaseAdapter",
    "InboundKind",
    "MessageEvent",
    "MessageHandler",
    "MessageType",
    "OutboundChannel",
    "WecomAdapter",
    "build_adapters",
]
