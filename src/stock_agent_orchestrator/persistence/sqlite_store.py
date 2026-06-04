from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from stock_agent_orchestrator.domain.models import AgentRole, ArtifactRef, EventType, Task, TaskEvent, TaskIntent, TaskStatus


SCHEMA = """
create table if not exists tasks (
  task_id text primary key,
  title text not null,
  intent text not null,
  owner text not null,
  status text not null,
  created_at text not null,
  updated_at text not null,
  current_assignee text not null,
  summary text not null,
  context_json text not null,
  artifacts_json text not null
);

create table if not exists task_events (
  id integer primary key autoincrement,
  task_id text not null,
  event_json text not null,
  foreign key(task_id) references tasks(task_id)
);
"""


class SQLiteTaskStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA)
        finally:
            conn.close()

    def save_task(self, task: Task) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                insert into tasks(task_id, title, intent, owner, status, created_at, updated_at, current_assignee, summary, context_json, artifacts_json)
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(task_id) do update set
                  title=excluded.title,
                  intent=excluded.intent,
                  owner=excluded.owner,
                  status=excluded.status,
                  created_at=excluded.created_at,
                  updated_at=excluded.updated_at,
                  current_assignee=excluded.current_assignee,
                  summary=excluded.summary,
                  context_json=excluded.context_json,
                  artifacts_json=excluded.artifacts_json
                """,
                (
                    task.task_id,
                    task.title,
                    task.intent.value,
                    task.owner.value,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.current_assignee.value,
                    task.summary,
                    json.dumps(task.context, ensure_ascii=False),
                    json.dumps([asdict(a) for a in task.artifacts], ensure_ascii=False),
                ),
            )
            conn.execute("delete from task_events where task_id = ?", (task.task_id,))
            conn.executemany(
                "insert into task_events(task_id, event_json) values(?, ?)",
                [
                    (task.task_id, json.dumps(self._event_to_dict(event), ensure_ascii=False))
                    for event in task.events
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def get_task_row(self, task_id: str) -> dict | None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute("select * from tasks where task_id = ?", (task_id,)).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def load_task(self, task_id: str) -> Task | None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute("select * from tasks where task_id = ?", (task_id,)).fetchone()
            if row is None:
                return None
            event_rows = conn.execute(
                "select event_json from task_events where task_id = ? order by id asc",
                (task_id,),
            ).fetchall()
        finally:
            conn.close()

        task = Task(
            task_id=row["task_id"],
            title=row["title"],
            intent=TaskIntent(row["intent"]),
            owner=AgentRole(row["owner"]),
            status=TaskStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            current_assignee=AgentRole(row["current_assignee"]),
            summary=row["summary"],
            context=json.loads(row["context_json"]),
            artifacts=[ArtifactRef(**artifact) for artifact in json.loads(row["artifacts_json"])],
            events=[],
        )
        for event_row in event_rows:
            payload = json.loads(event_row["event_json"])
            task.events.append(
                TaskEvent(
                    event_type=EventType(payload["event_type"]),
                    actor=AgentRole(payload["actor"]),
                    message=payload["message"],
                    created_at=datetime.fromisoformat(payload["created_at"]),
                    metadata=payload.get("metadata", {}),
                )
            )
        return task

    @staticmethod
    def _event_to_dict(event: TaskEvent) -> dict:
        payload = asdict(event)
        payload["event_type"] = event.event_type.value
        payload["actor"] = event.actor.value
        payload["created_at"] = event.created_at.isoformat()
        return payload
