from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from stock_agent_orchestrator.adapters.feishu_control import FeishuControlAdapter, FeishuEnvelope
from stock_agent_orchestrator.domain.models import AgentRole, EventType, Task, TaskEvent, TaskIntent, TaskStatus
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.task_engine import TaskEngine


@dataclass(slots=True)
class ShadowMessage:
    sender_name: str
    text: str
    created_at: str = ""
    mentions_owner: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ShadowFinding:
    task_id: str
    kind: str
    severity: str
    message: str


@dataclass(slots=True)
class ShadowReplayReport:
    imported_messages: int
    created_tasks: int
    advanced_events: int
    findings: list[ShadowFinding]
    tasks: list[dict[str, Any]]


RELAY_ACTION_PATTERN = re.compile(
    r"^(?P<logged_at>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) surface action: .*?"
    r"surface=(?P<surface>\S+) .*?"
    r"actor=(?P<actor>\S+) .*?"
    r"kind=(?P<kind>\S+) .*?"
    r"message=(?P<message_id>\S+) .*?"
    r"message_time=(?P<message_time>\S*) .*?"
    r'text="(?P<text>(?:\\.|[^"\\])*)"',
)

ACTOR_ALIASES = {
    "ou_bd0520ebd38cb4b8cae1f780677a95ae": "BOOS",
    "ou_116be0127b77068c571a2123f52c38c4": "小智",
    "ou_3f9a524344b25fdad435fb1c499f8f41": "小巴",
    "ou_99f804d2e8b10e12002ba95c2dbbf886": "小C",
}


class ShadowReplayService:
    def __init__(self, adapter: FeishuControlAdapter | None = None, engine: TaskEngine | None = None) -> None:
        self.adapter = adapter or FeishuControlAdapter()
        self.engine = engine or TaskEngine()

    def replay_file(self, input_path: Path, store: SQLiteTaskStore) -> ShadowReplayReport:
        messages = list(load_shadow_messages(input_path))
        store.init_db()
        tasks: list[Task] = []
        active_task: Task | None = None
        created = 0
        advanced = 0

        for index, message in enumerate(messages, start=1):
            command = self.adapter.parse(
                FeishuEnvelope(
                    sender_name=message.sender_name,
                    text=message.text,
                    mentions_owner=message.mentions_owner,
                )
            )
            if command is not None:
                if should_merge_command_into_active_task(active_task, command.intent, command.raw_text):
                    active_task = self._append_shadow_note(active_task, message, AgentRole.USER)
                    store.save_task(active_task)
                    tasks[-1] = active_task
                    advanced += 1
                    continue
                task = self.engine.create_task(
                    task_id=f"SHADOW-{index:04d}",
                    title=command.title,
                    intent=command.intent,
                    summary=command.raw_text,
                    context={"shadow_source": str(input_path), "auto_within_rules": command.auto_within_rules},
                )
                task.add_event(
                    TaskEvent(
                        EventType.NOTE,
                        AgentRole.SYSTEM,
                        "Shadow replay imported delegated message.",
                        metadata={"created_at": message.created_at, "sender_name": message.sender_name},
                    )
                )
                store.save_task(task)
                tasks.append(task)
                active_task = task
                created += 1
                continue

            if active_task is None:
                continue
            role = infer_agent_role(message.sender_name, message.text)
            if role is None:
                continue
            active_task = self._append_shadow_note(active_task, message, role)
            store.save_task(active_task)
            tasks[-1] = active_task
            advanced += 1

        findings = detect_stalls(tasks)
        return ShadowReplayReport(
            imported_messages=len(messages),
            created_tasks=created,
            advanced_events=advanced,
            findings=findings,
            tasks=[task_summary(task) for task in tasks],
        )

    def _append_shadow_note(self, task: Task, message: ShadowMessage, role: AgentRole) -> Task:
        task = self.engine.advance_task(
            task,
            actor=role,
            message=message.text,
            within_known_rules=is_known_rule_message(message.text),
            ask_user=is_waiting_user_message(message.text),
        )
        task.events[-1].metadata.update(
            {"shadow_created_at": message.created_at, "shadow_sender_name": message.sender_name}
        )
        return task


def load_shadow_messages(path: Path) -> Iterable[ShadowMessage]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            yield shadow_message_from_mapping(json.loads(line))
        return

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = line.strip()
        if not text:
            continue
        sender, _, body = text.partition(":")
        if body:
            yield ShadowMessage(
                sender_name=sender.strip(),
                text=body.strip(),
                mentions_owner=mentions_xiaoc(sender) or mentions_xiaoc(body),
            )
        else:
            yield ShadowMessage(sender_name="", text=text, mentions_owner=mentions_xiaoc(text))


def extract_relay_log_messages(log_path: Path, *, limit: int = 80) -> list[ShadowMessage]:
    messages: list[ShadowMessage] = []
    seen_message_ids: set[str] = set()
    for line in log_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = RELAY_ACTION_PATTERN.search(line)
        if match is None:
            continue
        kind = match.group("kind").strip()
        if kind != "surface.message.text":
            continue
        message_id = match.group("message_id").strip()
        if message_id in seen_message_ids:
            continue
        seen_message_ids.add(message_id)
        text = decode_go_quoted_text(match.group("text")).strip()
        if not text:
            continue
        actor = match.group("actor").strip()
        sender_name = ACTOR_ALIASES.get(actor, "用户" if actor.startswith("ou_") else "unknown")
        surface = match.group("surface").strip()
        messages.append(
            ShadowMessage(
                sender_name=sender_name,
                text=text,
                created_at=match.group("message_time").strip() or match.group("logged_at").strip(),
                mentions_owner=explicitly_mentions_xiaoc(text) or (":user:" in surface and sender_name == "BOOS"),
                raw={
                    "source": "codex-remote-relayd.log",
                    "kind": kind,
                    "actor_alias": sender_name,
                    "message_ref": f"msg-{len(messages) + 1:04d}",
                },
            )
        )
    if limit > 0:
        return messages[-limit:]
    return messages


def write_shadow_messages_jsonl(messages: Iterable[ShadowMessage], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for message in messages:
        rows.append(
            json.dumps(
                {
                    "sender_name": message.sender_name,
                    "text": message.text,
                    "created_at": message.created_at,
                    "mentions_owner": message.mentions_owner,
                },
                ensure_ascii=False,
            )
        )
    output_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def shadow_message_from_mapping(payload: dict[str, Any]) -> ShadowMessage:
    text = str(
        payload.get("text")
        or payload.get("message")
        or payload.get("content")
        or payload.get("SourceMessagePreview")
        or ""
    ).strip()
    sender_name = str(
        payload.get("sender_name")
        or payload.get("sender")
        or payload.get("actor")
        or payload.get("ActorUserID")
        or ""
    ).strip()
    created_at = str(payload.get("created_at") or payload.get("timestamp") or payload.get("RecordedAt") or "").strip()
    mentions_owner = bool(payload.get("mentions_owner")) or mentions_xiaoc(text)
    return ShadowMessage(
        sender_name=sender_name,
        text=text,
        created_at=created_at,
        mentions_owner=mentions_owner,
        raw=payload,
    )


def decode_go_quoted_text(value: str) -> str:
    value = value.replace('\\"', '"').replace("\\\\", "\\")
    raw = bytearray()
    i = 0
    while i < len(value):
        if value[i : i + 2] == "\\x" and i + 3 < len(value):
            try:
                raw.append(int(value[i + 2 : i + 4], 16))
                i += 4
                continue
            except ValueError:
                pass
        if value[i : i + 2] == "\\n":
            raw.append(ord("\n"))
            i += 2
            continue
        if value[i : i + 2] == "\\t":
            raw.append(ord("\t"))
            i += 2
            continue
        raw.extend(value[i].encode("utf-8", errors="replace"))
        i += 1
    return raw.decode("utf-8", errors="replace")


def infer_agent_role(sender_name: str, text: str) -> AgentRole | None:
    combined = f"{sender_name} {text}"
    if "小智" in combined or "xiaozhi" in combined.lower():
        return AgentRole.XIAOZHI
    if "小巴" in combined or "xiaoba" in combined.lower():
        return AgentRole.XIAOBA
    if "小C" in combined or "xiaoc" in combined.lower():
        return AgentRole.XIAOC
    if "BOOS" in combined or "用户" in combined or "user" in combined.lower():
        return AgentRole.USER
    return None


def detect_stalls(tasks: list[Task]) -> list[ShadowFinding]:
    findings: list[ShadowFinding] = []
    for task in tasks:
        if task.status == TaskStatus.WAITING_USER:
            findings.append(
                ShadowFinding(
                    task.task_id,
                    "waiting_user",
                    "info",
                    "任务停在用户审批，这是显式等待，不是静默断链。",
                )
            )
            continue
        if task.status not in {TaskStatus.RECORDED, TaskStatus.CLOSED}:
            findings.append(
                ShadowFinding(
                    task.task_id,
                    "silent_break",
                    "warning",
                    f"任务停在 {task.status.value}，当前责任人是 {task.current_assignee.value}。",
                )
            )
            continue
        if not task.artifacts and task.status in {TaskStatus.RECORDED, TaskStatus.CLOSED}:
            findings.append(
                ShadowFinding(
                    task.task_id,
                    "missing_evidence",
                    "warning",
                    "任务已收口但没有挂接证据产物，需要检查是否只发了消息没有落盘。",
                )
            )
    return findings


def task_summary(task: Task) -> dict[str, Any]:
    source_preview = task.summary.replace("\n", " ").strip()
    if len(source_preview) > 80:
        source_preview = source_preview[:79] + "…"
    return {
        "task_id": task.task_id,
        "title": task.title,
        "intent": task.intent.value,
        "status": task.status.value,
        "current_assignee": task.current_assignee.value,
        "event_count": len(task.events),
        "artifact_count": len(task.artifacts),
        "source_preview": source_preview,
    }


def report_to_dict(report: ShadowReplayReport) -> dict[str, Any]:
    return {
        "imported_messages": report.imported_messages,
        "created_tasks": report.created_tasks,
        "advanced_events": report.advanced_events,
        "findings": [asdict(finding) for finding in report.findings],
        "tasks": report.tasks,
    }


def report_to_markdown(report: ShadowReplayReport) -> str:
    lines = [
        "# Shadow Replay Report",
        "",
        f"- imported_messages: {report.imported_messages}",
        f"- created_tasks: {report.created_tasks}",
        f"- advanced_events: {report.advanced_events}",
        f"- findings: {len(report.findings)}",
        "",
        "## Tasks",
    ]
    for task in report.tasks:
        lines.append(
            f"- {task['task_id']} | {task['intent']} | {task['status']} | assignee={task['current_assignee']} | {task.get('source_preview', '')}"
        )
    lines.extend(["", "## Findings"])
    if not report.findings:
        lines.append("- none")
    for finding in report.findings:
        lines.append(f"- [{finding.severity}] {finding.task_id} {finding.kind}: {finding.message}")
    return "\n".join(lines) + "\n"


def mentions_xiaoc(text: str) -> bool:
    return "@小C" in text or "小C" in text or "@xiaoc" in text.lower()


def explicitly_mentions_xiaoc(text: str) -> bool:
    return "@小C" in text or "@xiaoc" in text.lower()


def is_known_rule_message(text: str) -> bool:
    return "新规则" not in text and "审批" not in text and "需要确认" not in text


def is_waiting_user_message(text: str) -> bool:
    return "需要你" in text or "请审批" in text or "等待审批" in text or "需要确认" in text


def should_merge_command_into_active_task(active_task: Task | None, intent: TaskIntent, text: str) -> bool:
    if active_task is None:
        return False
    if active_task.status in {TaskStatus.WAITING_USER, TaskStatus.RECORDED, TaskStatus.CLOSED}:
        return False
    followup_markers = (
        "继续",
        "下一步",
        "接着",
        "修正",
        "完善",
        "改善",
        "推进",
        "检查下",
        "看看",
        "现在进行到哪里",
    )
    if any(marker in text for marker in followup_markers):
        return True
    return active_task.intent == intent and len(active_task.events) < 8
