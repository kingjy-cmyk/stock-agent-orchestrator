from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from stock_agent_orchestrator.connectors.feishu import FeishuMessageEvent
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker, WorkerRunReport
from stock_agent_orchestrator.services.ingress import IngressItem


@dataclass(frozen=True, slots=True)
class WebhookResult:
    accepted: bool
    enqueued: bool = False
    challenge: str = ""
    reason: str = ""
    worker_report: WorkerRunReport | None = None


class FeishuWebhookGateway:
    """Minimal Feishu event-callback gateway.

    The gateway only normalizes platform payloads and enqueues work. Business
    state changes still happen in ConnectorWorker/BetaOrchestratorService.
    """

    def __init__(self, *, worker: ConnectorWorker, instance_id: str = "beta") -> None:
        self.worker = worker
        self.instance_id = instance_id

    def handle_payload(self, payload: dict[str, Any], *, drain: bool = False) -> WebhookResult:
        challenge = str(payload.get("challenge") or "").strip()
        if challenge:
            return WebhookResult(True, challenge=challenge, reason="url_verification")

        event = parse_message_event(payload)
        if event is None:
            return WebhookResult(False, reason="unsupported_payload")

        self.worker.enqueue(IngressItem(self.instance_id, event))
        report = self.worker.drain_once() if drain else None
        return WebhookResult(True, enqueued=True, worker_report=report)


def parse_message_event(payload: dict[str, Any]) -> FeishuMessageEvent | None:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    if not isinstance(event, dict):
        return None

    message = event.get("message") if isinstance(event.get("message"), dict) else event
    if not isinstance(message, dict):
        return None

    text = extract_text(message)
    chat_id = str(message.get("chat_id") or event.get("chat_id") or "").strip()
    if not text or not chat_id:
        return None

    sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
    sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    sender_open_id = str(
        message.get("sender_open_id")
        or event.get("sender_open_id")
        or sender_id.get("open_id")
        or sender_id.get("user_id")
        or ""
    ).strip()
    sender_name = str(message.get("sender_name") or event.get("sender_name") or event.get("operator_name") or "用户").strip()

    mentions = tuple(extract_mentions(message))
    return FeishuMessageEvent(
        event_id=str(payload.get("event_id") or payload.get("uuid") or message.get("message_id") or "").strip(),
        chat_id=chat_id,
        sender_open_id=sender_open_id,
        sender_name=sender_name,
        text=text,
        mentions=mentions,
        message_id=str(message.get("message_id") or "").strip(),
        created_at=str(message.get("create_time") or event.get("create_time") or "").strip(),
    )


def extract_text(message: dict[str, Any]) -> str:
    raw = message.get("content") or message.get("text") or ""
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return ""
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(decoded, dict):
            return str(decoded.get("text") or decoded.get("content") or "").strip()
        return raw
    if isinstance(raw, dict):
        return str(raw.get("text") or raw.get("content") or "").strip()
    return ""


def extract_mentions(message: dict[str, Any]) -> list[str]:
    mentions = message.get("mentions")
    if not isinstance(mentions, list):
        return []
    values: list[str] = []
    for item in mentions:
        if not isinstance(item, dict):
            continue
        mention_id = item.get("id") if isinstance(item.get("id"), dict) else {}
        for key in ("open_id", "user_id", "union_id"):
            value = str(item.get(key) or mention_id.get(key) or "").strip()
            if value:
                values.append(value)
    return values
