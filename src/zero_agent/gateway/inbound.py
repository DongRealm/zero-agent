"""Inbound event kinds from gateway platforms."""

from enum import StrEnum


class InboundKind(StrEnum):
    MESSAGE = "message"
    APPROVAL_RESPONSE = "approval_response"
    CARD_ACTION = "card_action"
