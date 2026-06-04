from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from stock_agent_orchestrator.connectors.feishu import FeishuOperationError


SCHEMA = """
create table if not exists gateway_counters (
  instance_id text primary key,
  accepted_count integer not null default 0,
  enqueued_count integer not null default 0,
  duplicate_count integer not null default 0,
  rate_limited_count integer not null default 0,
  operation_error_count integer not null default 0,
  last_error text not null default ''
);

create table if not exists gateway_seen_events (
  id integer primary key autoincrement,
  instance_id text not null,
  event_key text not null,
  created_at text not null,
  unique(instance_id, event_key)
);

create table if not exists gateway_operation_errors (
  id integer primary key autoincrement,
  instance_id text not null,
  kind text not null,
  chat_id text not null,
  task_id text not null,
  message text not null,
  created_at text not null
);
"""


@dataclass(frozen=True, slots=True)
class GatewayStateRow:
    accepted_count: int = 0
    enqueued_count: int = 0
    duplicate_count: int = 0
    rate_limited_count: int = 0
    operation_error_count: int = 0
    last_error: str = ""


class SQLiteGatewayStateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA)
            self._ensure_column(conn, "gateway_counters", "rate_limited_count", "integer not null default 0")
            conn.commit()
        finally:
            conn.close()

    def increment(self, instance_id: str, field: str, amount: int = 1) -> None:
        if field not in {"accepted_count", "enqueued_count", "duplicate_count", "rate_limited_count", "operation_error_count"}:
            raise ValueError(f"unsupported gateway counter: {field}")
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_counter_row(conn, instance_id)
            conn.execute(
                f"update gateway_counters set {field} = {field} + ? where instance_id = ?",
                (amount, instance_id),
            )
            conn.commit()
        finally:
            conn.close()

    def set_last_error(self, instance_id: str, message: str) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_counter_row(conn, instance_id)
            conn.execute(
                "update gateway_counters set last_error = ? where instance_id = ?",
                (message, instance_id),
            )
            conn.commit()
        finally:
            conn.close()

    def record_seen_key(self, instance_id: str, event_key: str, *, dedupe_window: int) -> bool:
        if not event_key:
            return False
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_counter_row(conn, instance_id)
            cursor = conn.execute(
                """
                insert or ignore into gateway_seen_events(instance_id, event_key, created_at)
                values(?, ?, ?)
                """,
                (instance_id, event_key, self._now()),
            )
            duplicate = cursor.rowcount == 0
            if dedupe_window > 0 and not duplicate:
                conn.execute(
                    """
                    delete from gateway_seen_events
                    where id in (
                      select id from gateway_seen_events
                      where instance_id = ?
                      order by id desc
                      limit -1 offset ?
                    )
                    """,
                    (instance_id, dedupe_window),
                )
            conn.commit()
            return duplicate
        finally:
            conn.close()

    def record_operation_error(self, instance_id: str, error: FeishuOperationError) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_counter_row(conn, instance_id)
            conn.execute(
                """
                insert into gateway_operation_errors(instance_id, kind, chat_id, task_id, message, created_at)
                values(?, ?, ?, ?, ?, ?)
                """,
                (instance_id, error.kind, error.chat_id, error.task_id, error.message, self._now()),
            )
            conn.execute(
                """
                update gateway_counters
                set operation_error_count = operation_error_count + 1,
                    last_error = ?
                where instance_id = ?
                """,
                (error.message, instance_id),
            )
            conn.commit()
        finally:
            conn.close()

    def load_snapshot(self, instance_id: str) -> GatewayStateRow:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            self._ensure_counter_row(conn, instance_id)
            row = conn.execute("select * from gateway_counters where instance_id = ?", (instance_id,)).fetchone()
            conn.commit()
            if row is None:
                return GatewayStateRow()
            return GatewayStateRow(
                accepted_count=int(row["accepted_count"]),
                enqueued_count=int(row["enqueued_count"]),
                duplicate_count=int(row["duplicate_count"]),
                rate_limited_count=int(row["rate_limited_count"]),
                operation_error_count=int(row["operation_error_count"]),
                last_error=str(row["last_error"] or ""),
            )
        finally:
            conn.close()

    def list_operation_errors(self, instance_id: str) -> list[FeishuOperationError]:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select kind, chat_id, task_id, message
                from gateway_operation_errors
                where instance_id = ?
                order by id asc
                """,
                (instance_id,),
            ).fetchall()
            return [
                FeishuOperationError(
                    kind=str(row["kind"]),
                    chat_id=str(row["chat_id"]),
                    task_id=str(row["task_id"]),
                    message=str(row["message"]),
                )
                for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def _ensure_counter_row(conn: sqlite3.Connection, instance_id: str) -> None:
        conn.execute("insert or ignore into gateway_counters(instance_id) values(?)", (instance_id,))

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {str(row[1]) for row in conn.execute(f"pragma table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"alter table {table} add column {column} {definition}")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
