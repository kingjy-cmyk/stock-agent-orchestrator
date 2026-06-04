from __future__ import annotations

from dataclasses import dataclass

from stock_agent_orchestrator.adapters.feishu_control import FeishuControlAdapter, FeishuEnvelope
from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.connectors.feishu import FeishuClient, FeishuMessageEvent, SentFeishuMessage
from stock_agent_orchestrator.domain.models import Task
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.task_card import render_task_card_markdown
from stock_agent_orchestrator.services.task_engine import TaskEngine


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
        feishu_client: FeishuClient,
        adapter: FeishuControlAdapter | None = None,
        engine: TaskEngine | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.feishu_client = feishu_client
        self.adapter = adapter or FeishuControlAdapter()
        self.engine = engine or TaskEngine()

    def process_message(self, event: FeishuMessageEvent) -> BetaProcessResult:
        if event.chat_id != self.config.feishu.group_chat_id:
            return BetaProcessResult(False, reason="chat_not_allowed")
        if self.config.project.environment != "beta" or self.config.project.mode != "active":
            return BetaProcessResult(False, reason="not_beta_active")

        command = self.adapter.parse(
            FeishuEnvelope(
                sender_name=event.sender_name,
                text=event.text,
                mentions_owner=event.mentions_open_id(self.config.feishu.owner_open_id),
            )
        )
        if command is None:
            return BetaProcessResult(False, reason="not_delegation")

        self.store.init_db()
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
        sent = self.feishu_client.send_message(event.chat_id, render_task_card_markdown(task))
        return BetaProcessResult(True, task_id=task.task_id, sent_message=sent)

    def _next_task_id(self) -> str:
        existing = self.store.list_tasks()
        return f"BETA-{len(existing) + 1:04d}"
