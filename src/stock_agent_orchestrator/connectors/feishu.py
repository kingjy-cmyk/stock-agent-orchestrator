from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FeishuMessageEvent:
    event_id: str
    chat_id: str
    sender_open_id: str
    sender_name: str
    text: str
    mentions: tuple[str, ...] = ()
    message_id: str = ""
    created_at: str = ""

    def mentions_open_id(self, open_id: str) -> bool:
        return open_id in self.mentions


@dataclass(frozen=True, slots=True)
class SentFeishuMessage:
    chat_id: str
    text: str
    message_id: str
    metadata: dict[str, str] = field(default_factory=dict)


class FeishuClient(Protocol):
    def send_message(self, chat_id: str, text: str) -> SentFeishuMessage:
        """Send a plain text or markdown-like message to a Feishu chat."""


class FakeFeishuClient:
    def __init__(self) -> None:
        self.sent_messages: list[SentFeishuMessage] = []

    def send_message(self, chat_id: str, text: str) -> SentFeishuMessage:
        message = SentFeishuMessage(
            chat_id=chat_id,
            text=text,
            message_id=f"fake-msg-{len(self.sent_messages) + 1:04d}",
            metadata={"client": "fake"},
        )
        self.sent_messages.append(message)
        return message
