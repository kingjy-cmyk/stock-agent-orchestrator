from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Protocol
from urllib.parse import quote
import urllib.request

from stock_agent_orchestrator.config import FeishuConfig


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


class FeishuOperationKind(StrEnum):
    SEND_TEXT = "send_text"
    SEND_CARD = "send_card"
    UPDATE_CARD = "update_card"


@dataclass(slots=True)
class FeishuOperation:
    kind: FeishuOperationKind
    chat_id: str
    text: str = ""
    message_id: str = ""
    reply_to_message_id: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FeishuOperationError:
    kind: str
    chat_id: str
    message: str
    task_id: str = ""


class FeishuClient(Protocol):
    def send_message(self, chat_id: str, text: str) -> SentFeishuMessage:
        """Send a plain text or markdown-like message to a Feishu chat."""

    def send_card(self, chat_id: str, markdown: str) -> SentFeishuMessage:
        """Send an updateable Feishu interactive card."""

    def update_card(self, message_id: str, markdown: str) -> SentFeishuMessage:
        """Update an existing Feishu interactive card by message_id."""


class FeishuOperationGateway(Protocol):
    def apply(self, operations: list[FeishuOperation]) -> list[SentFeishuMessage]:
        """Apply normalized Feishu operations."""


class OperationErrorRecorder(Protocol):
    def record_operation_error(self, error: FeishuOperationError) -> None:
        """Record a failed operation without coupling business logic to transport state."""


class FakeFeishuClient:
    def __init__(self) -> None:
        self.sent_messages: list[SentFeishuMessage] = []
        self.updated_messages: list[SentFeishuMessage] = []

    def send_message(self, chat_id: str, text: str) -> SentFeishuMessage:
        message = SentFeishuMessage(
            chat_id=chat_id,
            text=text,
            message_id=f"fake-msg-{len(self.sent_messages) + 1:04d}",
            metadata={"client": "fake"},
        )
        self.sent_messages.append(message)
        return message

    def send_card(self, chat_id: str, markdown: str) -> SentFeishuMessage:
        message = SentFeishuMessage(
            chat_id=chat_id,
            text=markdown,
            message_id=f"fake-msg-{len(self.sent_messages) + 1:04d}",
            metadata={
                "client": "fake",
                "operation": "send_card",
                "msg_type": "interactive",
                "content": json.dumps(feishu_card_content(markdown), ensure_ascii=False),
            },
        )
        self.sent_messages.append(message)
        return message

    def update_card(self, message_id: str, markdown: str) -> SentFeishuMessage:
        for index, message in enumerate(self.sent_messages):
            if message.message_id != message_id:
                continue
            updated = SentFeishuMessage(
                chat_id=message.chat_id,
                text=markdown,
                message_id=message_id,
                metadata={
                    "client": "fake",
                    "operation": "update_card",
                    "msg_type": "interactive",
                    "content": json.dumps(feishu_card_content(markdown), ensure_ascii=False),
                },
            )
            self.sent_messages[index] = updated
            self.updated_messages.append(updated)
            return updated
        raise RuntimeError(f"message_id not found for card update: {message_id}")


class ClientOperationGateway:
    def __init__(self, client: FeishuClient) -> None:
        self.client = client

    def apply(self, operations: list[FeishuOperation]) -> list[SentFeishuMessage]:
        results: list[SentFeishuMessage] = []
        for operation in operations:
            if operation.kind == FeishuOperationKind.SEND_TEXT:
                sent = self.client.send_message(operation.chat_id, operation.text)
            elif operation.kind == FeishuOperationKind.SEND_CARD:
                sent = self.client.send_card(operation.chat_id, operation.text)
            elif operation.kind == FeishuOperationKind.UPDATE_CARD:
                if not operation.message_id:
                    raise ValueError("update_card requires message_id")
                sent = self.client.update_card(operation.message_id, operation.text)
            else:
                raise NotImplementedError(f"unsupported operation: {operation.kind}")
            operation.message_id = sent.message_id
            results.append(sent)
        return results


class GuardedOperationGateway:
    """Safety wrapper for live-capable operation gateways."""

    def __init__(
        self,
        delegate: FeishuOperationGateway,
        *,
        allowed_chat_ids: set[str],
        error_recorder: OperationErrorRecorder | None = None,
    ) -> None:
        self.delegate = delegate
        self.allowed_chat_ids = {chat_id.strip() for chat_id in allowed_chat_ids if chat_id.strip()}
        self.error_recorder = error_recorder

    def apply(self, operations: list[FeishuOperation]) -> list[SentFeishuMessage]:
        for operation in operations:
            if operation.chat_id.strip() not in self.allowed_chat_ids:
                message = f"chat_id not in send allowlist: {operation.chat_id}"
                self._record_error(operation, message)
                raise RuntimeError(message)
        try:
            return self.delegate.apply(operations)
        except Exception as exc:
            for operation in operations:
                self._record_error(operation, str(exc))
            raise

    def _record_error(self, operation: FeishuOperation, message: str) -> None:
        if self.error_recorder is None:
            return
        self.error_recorder.record_operation_error(
            FeishuOperationError(
                kind=str(operation.kind),
                chat_id=operation.chat_id,
                message=message,
                task_id=operation.metadata.get("task_id", ""),
            )
        )


class LiveFeishuClient:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        api_base_url: str = "https://open.feishu.cn",
        opener: Callable[[urllib.request.Request], Any] | None = None,
    ) -> None:
        self.app_id = app_id.strip()
        self.app_secret = app_secret.strip()
        self.api_base_url = api_base_url.rstrip("/")
        self.opener = opener or urllib.request.urlopen
        self._tenant_access_token = ""

    def send_message(self, chat_id: str, text: str) -> SentFeishuMessage:
        token = self._tenant_token()
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        response = self._post_json(
            f"{self.api_base_url}/open-apis/im/v1/messages?receive_id_type=chat_id",
            payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        message_id = str(data.get("message_id") or data.get("messageId") or "")
        return SentFeishuMessage(
            chat_id=chat_id,
            text=text,
            message_id=message_id,
            metadata={"client": "live", "api": "im.v1.message.create"},
        )

    def send_card(self, chat_id: str, markdown: str) -> SentFeishuMessage:
        token = self._tenant_token()
        payload = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(feishu_card_content(markdown), ensure_ascii=False),
        }
        response = self._post_json(
            f"{self.api_base_url}/open-apis/im/v1/messages?receive_id_type=chat_id",
            payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        message_id = str(data.get("message_id") or data.get("messageId") or "")
        return SentFeishuMessage(
            chat_id=chat_id,
            text=markdown,
            message_id=message_id,
            metadata={"client": "live", "api": "im.v1.message.create", "msg_type": "interactive"},
        )

    def update_card(self, message_id: str, markdown: str) -> SentFeishuMessage:
        token = self._tenant_token()
        self._post_json(
            f"{self.api_base_url}/open-apis/im/v1/messages/{quote(message_id, safe='')}",
            {"content": json.dumps(feishu_card_content(markdown), ensure_ascii=False)},
            headers={"Authorization": f"Bearer {token}"},
            method="PATCH",
        )
        return SentFeishuMessage(
            chat_id="",
            text=markdown,
            message_id=message_id,
            metadata={"client": "live", "api": "im.v1.message.patch", "msg_type": "interactive"},
        )

    def _tenant_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token
        response = self._post_json(
            f"{self.api_base_url}/open-apis/auth/v3/tenant_access_token/internal",
            {"app_id": self.app_id, "app_secret": self.app_secret},
        )
        token = str(response.get("tenant_access_token") or "")
        if not token:
            raise RuntimeError("Feishu tenant_access_token missing in response")
        self._tenant_access_token = token
        return token

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        method: str = "POST",
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})},
            method=method,
        )
        with self.opener(request) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("Feishu API response must be an object")
        code = data.get("code", 0)
        if code not in (0, "0", None):
            raise RuntimeError(f"Feishu API error: code={code} msg={data.get('msg') or data.get('message')}")
        return data


def build_feishu_client(config: FeishuConfig, *, allow_live_send: bool = False) -> FeishuClient:
    if config.send_mode != "live":
        return FakeFeishuClient()
    if not allow_live_send:
        raise RuntimeError("live Feishu send requires explicit allow_live_send=True")
    return LiveFeishuClient(
        app_id=config.app_id,
        app_secret=config.app_secret,
        api_base_url=config.api_base_url,
    )


def feishu_card_content(markdown: str) -> dict[str, Any]:
    """Build a shared card that Feishu can update later via message_id PATCH."""

    return {
        "config": {"update_multi": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "多 Agent 任务卡"},
        },
        "elements": [
            {
                "tag": "markdown",
                "content": markdown,
            }
        ],
    }


def build_operation_gateway(
    config: FeishuConfig,
    *,
    allow_live_send: bool = False,
    error_recorder: OperationErrorRecorder | None = None,
) -> FeishuOperationGateway:
    allowed_chat_ids = set(config.send_allowlist or [config.group_chat_id])
    return GuardedOperationGateway(
        ClientOperationGateway(build_feishu_client(config, allow_live_send=allow_live_send)),
        allowed_chat_ids=allowed_chat_ids,
        error_recorder=error_recorder,
    )
