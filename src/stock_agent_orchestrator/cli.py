from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from stock_agent_orchestrator.bridges.current_stack import CurrentStackBridge
from stock_agent_orchestrator.domain.models import AgentRole, TaskIntent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.rule_memory import RuleMemoryService
from stock_agent_orchestrator.services.shadow_replay import ShadowReplayService, report_to_dict, report_to_markdown
from stock_agent_orchestrator.services.task_engine import TaskEngine


DEFAULT_DB = Path(".runtime/stock-agent-orchestrator.db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stock-agent-orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    init_db = sub.add_parser("init-db")
    init_db.add_argument("--db", default=str(DEFAULT_DB))

    new_task = sub.add_parser("new-task")
    new_task.add_argument("--db", default=str(DEFAULT_DB))
    new_task.add_argument("--task-id", default="TASK-0001")
    new_task.add_argument("--title", required=True)
    new_task.add_argument("--intent", choices=[intent.value for intent in TaskIntent], required=True)
    new_task.add_argument("--summary", default="")

    show_task = sub.add_parser("show-task")
    show_task.add_argument("--db", default=str(DEFAULT_DB))
    show_task.add_argument("--task-id", required=True)

    advance_task = sub.add_parser("advance-task")
    advance_task.add_argument("--db", default=str(DEFAULT_DB))
    advance_task.add_argument("--task-id", required=True)
    advance_task.add_argument("--actor", choices=[role.value for role in AgentRole if role not in {AgentRole.SYSTEM, AgentRole.USER}], required=True)
    advance_task.add_argument("--message", required=True)
    advance_task.add_argument("--novel-rule", action="store_true")
    advance_task.add_argument("--ask-user", action="store_true")

    resume_task = sub.add_parser("resume-task")
    resume_task.add_argument("--db", default=str(DEFAULT_DB))
    resume_task.add_argument("--task-id", required=True)
    resume_task.add_argument("--message", required=True)

    suggest_rules = sub.add_parser("suggest-rules")
    suggest_rules.add_argument("--db", default=str(DEFAULT_DB))
    suggest_rules.add_argument("--task-id", required=True)

    ingest = sub.add_parser("ingest-candidates")
    ingest.add_argument("--candidate-file", required=True)

    parse_report = sub.add_parser("parse-seven-layer")
    parse_report.add_argument("--report-file", required=True)

    shadow = sub.add_parser("shadow-replay")
    shadow.add_argument("--db", default=str(DEFAULT_DB))
    shadow.add_argument("--input", required=True)
    shadow.add_argument("--report", default="")
    shadow.add_argument("--format", choices=["json", "markdown"], default="json")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "init-db":
        store = SQLiteTaskStore(Path(args.db))
        store.init_db()
        print(Path(args.db).resolve())
        return

    if args.command == "new-task":
        store = SQLiteTaskStore(Path(args.db))
        store.init_db()
        engine = TaskEngine()
        task = engine.create_task(
            task_id=args.task_id,
            title=args.title,
            intent=TaskIntent(args.intent),
            summary=args.summary,
        )
        store.save_task(task)
        print(task.task_id)
        print(task.status.value)
        print(task.current_assignee.value)
        return

    if args.command == "show-task":
        store = SQLiteTaskStore(Path(args.db))
        task = store.load_task(args.task_id)
        if task is None:
            raise SystemExit(f"task not found: {args.task_id}")
        print(json.dumps({
            "task_id": task.task_id,
            "title": task.title,
            "intent": task.intent.value,
            "owner": task.owner.value,
            "status": task.status.value,
            "current_assignee": task.current_assignee.value,
            "summary": task.summary,
            "context": task.context,
            "artifacts": [asdict(artifact) for artifact in task.artifacts],
            "events": [
                {
                    "event_type": event.event_type.value,
                    "actor": event.actor.value,
                    "message": event.message,
                    "created_at": event.created_at.isoformat(),
                    "metadata": event.metadata,
                }
                for event in task.events
            ],
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "advance-task":
        store = SQLiteTaskStore(Path(args.db))
        task = store.load_task(args.task_id)
        if task is None:
            raise SystemExit(f"task not found: {args.task_id}")
        engine = TaskEngine()
        task = engine.advance_task(
            task,
            actor=AgentRole(args.actor),
            message=args.message,
            within_known_rules=not args.novel_rule,
            ask_user=args.ask_user,
        )
        store.save_task(task)
        print(task.status.value)
        print(task.current_assignee.value)
        return

    if args.command == "resume-task":
        store = SQLiteTaskStore(Path(args.db))
        task = store.load_task(args.task_id)
        if task is None:
            raise SystemExit(f"task not found: {args.task_id}")
        engine = TaskEngine()
        task = engine.resume_from_user(task, args.message)
        store.save_task(task)
        print(task.status.value)
        print(task.current_assignee.value)
        return

    if args.command == "suggest-rules":
        store = SQLiteTaskStore(Path(args.db))
        task = store.load_task(args.task_id)
        if task is None:
            raise SystemExit(f"task not found: {args.task_id}")
        suggestions = RuleMemoryService().suggest_updates(task)
        print(json.dumps([asdict(item) for item in suggestions], ensure_ascii=False, indent=2))
        return

    if args.command == "ingest-candidates":
        bridge = CurrentStackBridge()
        snapshot = bridge.read_candidate_pool(Path(args.candidate_file))
        print(json.dumps({
            "source_path": snapshot.source_path,
            "count": len(snapshot.candidates),
            "candidates": [asdict(candidate) for candidate in snapshot.candidates[:10]],
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "parse-seven-layer":
        bridge = CurrentStackBridge()
        cards = bridge.parse_seven_layer_report(Path(args.report_file))
        print(json.dumps([asdict(card) for card in cards], ensure_ascii=False, indent=2))
        return

    if args.command == "shadow-replay":
        store = SQLiteTaskStore(Path(args.db))
        report = ShadowReplayService().replay_file(Path(args.input), store)
        rendered = (
            report_to_markdown(report)
            if args.format == "markdown"
            else json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)
        )
        if args.report:
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report).write_text(rendered, encoding="utf-8")
        print(rendered)
        return


if __name__ == "__main__":
    main()
