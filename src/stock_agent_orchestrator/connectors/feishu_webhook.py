from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

from stock_agent_orchestrator.connectors.feishu import FeishuMessageEvent, FeishuOperationError, OperationErrorRecorder
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker, WorkerRunReport
from stock_agent_orchestrator.services.ingress import IngressItem


@dataclass(frozen=True, slots=True)
class WebhookResult:
    accepted: bool
    enqueued: bool = False
    challenge: str = ""
    reason: str = ""
    worker_report: WorkerRunReport | None = None


@dataclass(frozen=True, slots=True)
class GatewayStateSnapshot:
    status: str
    accepted_count: int
    enqueued_count: int
    duplicate_count: int
    operation_error_count: int
    last_error: str = ""


class FeishuWebhookGateway(OperationErrorRecorder):
    """Minimal Feishu event-callback gateway.

    The gateway only normalizes platform payloads and enqueues work. Business
    state changes still happen in ConnectorWorker/BetaOrchestratorService.
    """

    def __init__(
        self,
        *,
        worker: ConnectorWorker | None = None,
        instance_id: str = "beta",
        dedupe_window: int = 2048,
    ) -> None:
        self.worker = worker
        self.instance_id = instance_id
        self.dedupe_window = dedupe_window
        self._seen_keys: set[str] = set()
        self._seen_order: deque[str] = deque()
        self._accepted_count = 0
        self._enqueued_count = 0
        self._duplicate_count = 0
        self._operation_errors: list[FeishuOperationError] = []
        self._last_error = ""

    def handle_payload(self, payload: dict[str, Any], *, drain: bool = False) -> WebhookResult:
        if self.worker is None:
            self._last_error = "worker_not_attached"
            return WebhookResult(False, reason="worker_not_attached")

        challenge = str(payload.get("challenge") or "").strip()
        if challenge:
            self._accepted_count += 1
            return WebhookResult(True, challenge=challenge, reason="url_verification")

        event = parse_message_event(payload)
        if event is None:
            self._last_error = "unsupported_payload"
            return WebhookResult(False, reason="unsupported_payload")

        self._accepted_count += 1
        if self._is_duplicate(event):
            self._duplicate_count += 1
            return WebhookResult(True, enqueued=False, reason="duplicate_event")

        self.worker.enqueue(IngressItem(self.instance_id, event))
        self._enqueued_count += 1
        report = self.worker.drain_once() if drain else None
        return WebhookResult(True, enqueued=True, worker_report=report)

    def attach_worker(self, worker: ConnectorWorker) -> None:
        self.worker = worker

    def record_operation_error(self, error: FeishuOperationError) -> None:
        self._operation_errors.append(error)
        self._last_error = error.message

    def state_snapshot(self) -> GatewayStateSnapshot:
        status = "connected"
        if self._last_error:
            status = "degraded"
        return GatewayStateSnapshot(
            status=status,
            accepted_count=self._accepted_count,
            enqueued_count=self._enqueued_count,
            duplicate_count=self._duplicate_count,
            operation_error_count=len(self._operation_errors),
            last_error=self._last_error,
        )

    def state_dict(self) -> dict[str, Any]:
        return asdict(self.state_snapshot())

    def operation_errors(self) -> list[FeishuOperationError]:
        return list(self._operation_errors)

    def _is_duplicate(self, event: FeishuMessageEvent) -> bool:
        key = event.event_id or event.message_id
        if not key:
            return False
        if key in self._seen_keys:
            return True
        self._seen_keys.add(key)
        self._seen_order.append(key)
        while self.dedupe_window > 0 and len(self._seen_order) > self.dedupe_window:
            expired = self._seen_order.popleft()
            self._seen_keys.discard(expired)
        return False


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
