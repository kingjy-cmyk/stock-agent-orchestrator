from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentRole(StrEnum):
    XIAOC = "xiaoc"
    XIAOZHI = "xiaozhi"
    XIAOBA = "xiaoba"
    USER = "user"
    SYSTEM = "system"


class TaskIntent(StrEnum):
    DAILY_CANDIDATE_POOL = "daily_candidate_pool"
    SINGLE_STOCK_RESEARCH = "single_stock_research"
    RULE_UPDATE = "rule_update"


class TaskStatus(StrEnum):
    NEW = "new"
    PLANNED = "planned"
    SCANNING = "scanning"
    ENRICHING = "enriching"
    ANALYZING = "analyzing"
    FOLLOWING_UP = "following_up"
    WAITING_USER = "waiting_user"
    RECORDED = "recorded"
    CLOSED = "closed"


class EventType(StrEnum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    NOTE = "note"
    ARTIFACT_ATTACHED = "artifact_attached"
    QUESTION = "question"
    CLOSED = "closed"


@dataclass(slots=True)
class ArtifactRef:
    kind: str
    path: str
    summary: str = ""


@dataclass(slots=True)
class TaskEvent:
    event_type: EventType
    actor: AgentRole
    message: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Task:
    task_id: str
    title: str
    intent: TaskIntent
    owner: AgentRole = AgentRole.XIAOC
    status: TaskStatus = TaskStatus.NEW
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    current_assignee: AgentRole = AgentRole.XIAOC
    summary: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    artifacts: list[ArtifactRef] = field(default_factory=list)
    events: list[TaskEvent] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def add_event(self, event: TaskEvent) -> None:
        self.events.append(event)
        self.touch()

    def add_artifact(self, artifact: ArtifactRef) -> None:
        self.artifacts.append(artifact)
        self.touch()

