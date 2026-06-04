from __future__ import annotations

import re
from dataclasses import dataclass

from stock_agent_orchestrator.adapters.feishu_control import FeishuControlAdapter, FeishuEnvelope
from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.connectors.feishu import (
    ClientOperationGateway,
    FeishuClient,
    FeishuMessageEvent,
    FeishuOperation,
    FeishuOperationGateway,
    FeishuOperationKind,
    SentFeishuMessage,
)
from stock_agent_orchestrator.domain.models import AgentRole, Task, TaskStatus
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.task_card import render_task_card_markdown
from stock_agent_orchestrator.services.task_engine import TaskEngine


TASK_ID_PATTERN = re.compile(r"\bBETA-\d{4,}\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class BetaProcessResult:
    handled: bool
    task_id: str = ""
    sent_message: SentFeishuMessage | None = None
    reason: str = ""


class BetaOrchestratorService:
    def __init__(
        self,
        *,
        config: OrchestratorConfig,
        store: SQLiteTaskStore,
        feishu_client: FeishuClient | None = None,
        operation_gateway: FeishuOperationGateway | None = None,
        adapter: FeishuControlAdapter | None = None,
        engine: TaskEngine | None = None,
    ) -> None:
        self.config = config
        self.store = store
        if operation_gateway is None and feishu_client is None:
            raise ValueError("BetaOrchestratorService requires feishu_client or operation_gateway")
        self.operation_gateway = operation_gateway or ClientOperationGateway(feishu_client)  # type: ignore[arg-type]
        self.adapter = adapter or FeishuControlAdapter()
        self.engine = engine or TaskEngine()

    def process_message(self, event: FeishuMessageEvent) -> BetaProcessResult:
        if event.chat_id != self.config.feishu.group_chat_id:
            return BetaProcessResult(False, reason="chat_not_allowed")
        if self.config.project.environment != "beta" or self.config.project.mode != "active":
            return BetaProcessResult(False, reason="not_beta_active")

        self.store.init_db()
        if actor := self._agent_actor(event.sender_open_id):
            return self._process_agent_update(event, actor)

        command = self.adapter.parse(
            FeishuEnvelope(
                sender_name=event.sender_name,
                text=event.text,
                mentions_owner=event.mentions_open_id(self.config.feishu.owner_open_id),
            )
        )
        if command is None:
            return BetaProcessResult(False, reason="not_delegation")

        task = self.engine.create_task(
            task_id=self._next_task_id(),
            title=command.title,
            intent=command.intent,
            summary=command.raw_text,
            context={
                "source": "feishu_beta",
                "chat_id": event.chat_id,
                "message_id": event.message_id,
                "event_id": event.event_id,
                "auto_within_rules": command.auto_within_rules,
            },
        )
        self.store.save_task(task)
        return self._send_task_card(event.chat_id, task)

    def _process_agent_update(self, event: FeishuMessageEvent, actor: AgentRole) -> BetaProcessResult:
        task = self._target_task(event)
        if task is None:
            return BetaProcessResult(False, reason="no_open_task")
        task.context["last_agent_message_id"] = event.message_id
        task.context["last_agent_event_id"] = event.event_id
        task = self.engine.advance_task(
            task,
            actor=actor,
            message=event.text,
            within_known_rules=True,
        )
        self.store.save_task(task)
        return self._send_task_card(event.chat_id, task)

    def _send_task_card(self, chat_id: str, task: Task) -> BetaProcessResult:
        existing_card_message_id = str(task.context.get("task_card_message_id") or "")
        operation_kind = FeishuOperationKind.UPDATE_CARD if existing_card_message_id else FeishuOperationKind.SEND_CARD
        try:
            sent = self.operation_gateway.apply(
                [
                    FeishuOperation(
                        kind=operation_kind,
                        chat_id=chat_id,
                        text=render_task_card_markdown(task),
                        message_id=existing_card_message_id,
                        metadata={"task_id": task.task_id},
                    )
                ]
            )[0]
        except Exception as exc:
            return BetaProcessResult(False, task_id=task.task_id, reason=f"operation_error:{exc}")
        if sent.message_id:
            task.context.setdefault("task_card_message_id", sent.message_id)
            task.context["latest_task_card_message_id"] = sent.message_id
            if operation_kind == FeishuOperationKind.SEND_CARD:
                task.context["task_card_send_count"] = int(task.context.get("task_card_send_count") or 0) + 1
            else:
                task.context["task_card_update_count"] = int(task.context.get("task_card_update_count") or 0) + 1
            self.store.save_task(task)
        return BetaProcessResult(True, task_id=task.task_id, sent_message=sent)

    def _next_task_id(self) -> str:
        existing = self.store.list_tasks()
        return f"BETA-{len(existing) + 1:04d}"

    def _agent_actor(self, sender_open_id: str) -> AgentRole | None:
        sender = sender_open_id.strip()
        if sender == self.config.feishu.data_open_id.strip():
            return AgentRole.XIAOZHI
        if sender == self.config.feishu.analyst_open_id.strip():
            return AgentRole.XIAOBA
        return None

    def _latest_open_task(self, chat_id: str) -> Task | None:
        for task in reversed(self.store.list_tasks()):
            if task.context.get("chat_id") != chat_id:
                continue
            if task.status in {TaskStatus.CLOSED, TaskStatus.RECORDED}:
                continue
            return task
        return None

    def _target_task(self, event: FeishuMessageEvent) -> Task | None:
        if task_id := self._extract_task_id(event.text):
            task = self.store.load_task(task_id)
            if task is None:
                return None
            if task.context.get("chat_id") != event.chat_id:
                return None
            if task.status in {TaskStatus.CLOSED, TaskStatus.RECORDED}:
                return None
            return task
        return self._latest_open_task(event.chat_id)

    def _extract_task_id(self, text: str) -> str:
        match = TASK_ID_PATTERN.search(text)
        return match.group(0).upper() if match else ""
