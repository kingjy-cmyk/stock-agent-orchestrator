from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from stock_agent_orchestrator.bridges.current_stack import CurrentStackBridge
from stock_agent_orchestrator.config import config_to_dict, load_config, validate_config, validation_to_dict
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient, FeishuMessageEvent
from stock_agent_orchestrator.connectors.feishu_http import build_webhook_server_from_config
from stock_agent_orchestrator.connectors.feishu_webhook import FeishuWebhookGateway
from stock_agent_orchestrator.domain.models import AgentRole, TaskIntent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker
from stock_agent_orchestrator.services.demo import write_demo_sample
from stock_agent_orchestrator.services.doctor import doctor_report_to_dict, run_doctor
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue, IngressItem
from stock_agent_orchestrator.services.rule_memory import RuleMemoryService
from stock_agent_orchestrator.services.shadow_replay import (
    ShadowReplayService,
    extract_relay_log_messages,
    report_to_dict,
    report_to_markdown,
    write_shadow_messages_jsonl,
)
from stock_agent_orchestrator.services.task_card import render_task_card_markdown
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

    extract = sub.add_parser("extract-relay-log")
    extract.add_argument("--log-file", required=True)
    extract.add_argument("--output", required=True)
    extract.add_argument("--limit", type=int, default=80)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--runtime-dir", default=".runtime")

    demo = sub.add_parser("demo")
    demo.add_argument("--runtime-dir", default=".runtime")
    demo.add_argument("--format", choices=["json", "markdown"], default="markdown")

    validate_config_cmd = sub.add_parser("validate-config")
    validate_config_cmd.add_argument("--config", required=True)

    render_card = sub.add_parser("render-task-card")
    render_card.add_argument("--db", default=str(DEFAULT_DB))
    render_card.add_argument("--task-id", required=True)
    render_card.add_argument("--format", choices=["json", "markdown"], default="markdown")

    beta_smoke = sub.add_parser("beta-smoke")
    beta_smoke.add_argument("--config", default="configs/beta.example.toml")
    beta_smoke.add_argument("--db", default=".runtime/beta-smoke.db")
    beta_smoke.add_argument("--text", default="@小C-beta 今天先给我一份候选池")

    worker_smoke = sub.add_parser("worker-smoke")
    worker_smoke.add_argument("--config", default="configs/beta.example.toml")
    worker_smoke.add_argument("--db", default=".runtime/worker-smoke.db")
    worker_smoke.add_argument("--max-per-instance", type=int, default=16)

    webhook_smoke = sub.add_parser("webhook-smoke")
    webhook_smoke.add_argument("--config", default="configs/beta.example.toml")
    webhook_smoke.add_argument("--db", default=".runtime/webhook-smoke.db")
    webhook_smoke.add_argument("--text", default="@小C-beta 今天先给我一份候选池")

    run_webhook = sub.add_parser("run-webhook")
    run_webhook.add_argument("--config", default="configs/beta.example.toml")
    run_webhook.add_argument("--db", default=".runtime/webhook.db")
    run_webhook.add_argument("--host", default="127.0.0.1")
    run_webhook.add_argument("--port", type=int, default=8787)
    run_webhook.add_argument("--max-per-instance", type=int, default=1024)

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

    if args.command == "extract-relay-log":
        messages = extract_relay_log_messages(Path(args.log_file), limit=args.limit)
        write_shadow_messages_jsonl(messages, Path(args.output))
        print(Path(args.output).resolve())
        print(len(messages))
        return

    if args.command == "doctor":
        report = run_doctor(Path(args.runtime_dir))
        print(json.dumps(doctor_report_to_dict(report), ensure_ascii=False, indent=2))
        if not report.ok:
            raise SystemExit(1)
        return

    if args.command == "demo":
        runtime_dir = Path(args.runtime_dir)
        sample_path = write_demo_sample(runtime_dir / "demo-shadow-sample.jsonl")
        db_path = runtime_dir / "demo.db"
        report = ShadowReplayService().replay_file(sample_path, SQLiteTaskStore(db_path))
        rendered = (
            report_to_markdown(report)
            if args.format == "markdown"
            else json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)
        )
        report_path = runtime_dir / f"demo-shadow-report.{'md' if args.format == 'markdown' else 'json'}"
        report_path.write_text(rendered, encoding="utf-8")
        print(rendered)
        print(f"sample={sample_path.resolve()}")
        print(f"report={report_path.resolve()}")
        return

    if args.command == "validate-config":
        config = load_config(Path(args.config))
        issues = validate_config(config)
        print(json.dumps({
            "config": config_to_dict(config),
            "issues": validation_to_dict(issues),
            "ok": not any(issue.severity == "error" for issue in issues),
        }, ensure_ascii=False, indent=2))
        if any(issue.severity == "error" for issue in issues):
            raise SystemExit(1)
        return

    if args.command == "render-task-card":
        store = SQLiteTaskStore(Path(args.db))
        task = store.load_task(args.task_id)
        if task is None:
            raise SystemExit(f"task not found: {args.task_id}")
        if args.format == "markdown":
            print(render_task_card_markdown(task))
        else:
            print(json.dumps({
                "task_id": task.task_id,
                "card_markdown": render_task_card_markdown(task),
            }, ensure_ascii=False, indent=2))
        return

    if args.command == "beta-smoke":
        config = load_config(Path(args.config))
        store = SQLiteTaskStore(Path(args.db))
        client = FakeFeishuClient()
        result = BetaOrchestratorService(config=config, store=store, feishu_client=client).process_message(
            FeishuMessageEvent(
                event_id="smoke-event-1",
                chat_id=config.feishu.group_chat_id,
                sender_open_id="smoke-user",
                sender_name="BOOS",
                text=args.text,
                mentions=(config.feishu.owner_open_id,),
                message_id="smoke-message-1",
            )
        )
        print(json.dumps({
            "handled": result.handled,
            "task_id": result.task_id,
            "reason": result.reason,
            "sent_messages": [
                {
                    "chat_id": message.chat_id,
                    "message_id": message.message_id,
                    "text": message.text,
                }
                for message in client.sent_messages
            ],
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "worker-smoke":
        config = load_config(Path(args.config))
        client = FakeFeishuClient()
        worker = ConnectorWorker(
            queue=BoundedIngressQueue(max_per_instance=args.max_per_instance),
            orchestrator=BetaOrchestratorService(
                config=config,
                store=SQLiteTaskStore(Path(args.db)),
                feishu_client=client,
            ),
        )
        for index, text in enumerate(
            [
                "@小C-beta 今天先给我一份候选池",
                "测试",
                "@小C-beta 研究一下山西汾酒七层数据",
            ],
            start=1,
        ):
            worker.enqueue(
                IngressItem(
                    "beta",
                    FeishuMessageEvent(
                        event_id=f"worker-smoke-event-{index}",
                        chat_id=config.feishu.group_chat_id,
                        sender_open_id="smoke-user",
                        sender_name="BOOS",
                        text=text,
                        mentions=(config.feishu.owner_open_id,),
                        message_id=f"worker-smoke-message-{index}",
                    ),
                )
            )
        report = worker.drain_once()
        stats = worker.stats("beta")
        print(json.dumps({
            "processed": report.processed,
            "handled": report.handled,
            "ignored": report.ignored,
            "queue": {
                "current_depth": stats.current_depth,
                "peak_depth": stats.peak_depth,
                "overload_count": stats.overload_count,
            },
            "sent_messages": [
                {
                    "chat_id": message.chat_id,
                    "message_id": message.message_id,
                    "text": message.text,
                }
                for message in client.sent_messages
            ],
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "webhook-smoke":
        config = load_config(Path(args.config))
        client = FakeFeishuClient()
        worker = ConnectorWorker(
            queue=BoundedIngressQueue(max_per_instance=16),
            orchestrator=BetaOrchestratorService(
                config=config,
                store=SQLiteTaskStore(Path(args.db)),
                feishu_client=client,
            ),
        )
        gateway = FeishuWebhookGateway(worker=worker)
        challenge = gateway.handle_payload({"challenge": "stock-agent-orchestrator"})
        message = gateway.handle_payload(
            {
                "event_id": "webhook-smoke-event-1",
                "event": {
                    "sender": {"sender_id": {"open_id": "smoke-user"}},
                    "message": {
                        "message_id": "webhook-smoke-message-1",
                        "chat_id": config.feishu.group_chat_id,
                        "chat_type": "group",
                        "content": json.dumps({"text": args.text}, ensure_ascii=False),
                        "mentions": [{"id": {"open_id": config.feishu.owner_open_id}, "name": config.roles.owner}],
                        "create_time": "",
                    },
                },
            },
            drain=True,
        )
        print(json.dumps({
            "challenge": {
                "accepted": challenge.accepted,
                "value": challenge.challenge,
            },
            "message": {
                "accepted": message.accepted,
                "enqueued": message.enqueued,
                "reason": message.reason,
                "worker": {
                    "processed": message.worker_report.processed if message.worker_report else 0,
                    "handled": message.worker_report.handled if message.worker_report else 0,
                    "ignored": message.worker_report.ignored if message.worker_report else 0,
                },
            },
            "sent_messages": [
                {
                    "chat_id": sent.chat_id,
                    "message_id": sent.message_id,
                    "text": sent.text,
                }
                for sent in client.sent_messages
            ],
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "run-webhook":
        server = build_webhook_server_from_config(
            host=args.host,
            port=args.port,
            config_path=Path(args.config),
            db_path=Path(args.db),
            max_per_instance=args.max_per_instance,
        )
        print(json.dumps({
            "ok": True,
            "mode": "fake-send",
            "listen": f"http://{args.host}:{server.server_address[1]}",
            "webhook": f"http://{args.host}:{server.server_address[1]}/webhook",
            "healthz": f"http://{args.host}:{server.server_address[1]}/healthz",
            "note": "Uses FakeFeishuClient; does not send to a real Feishu group yet.",
        }, ensure_ascii=False, indent=2))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return


if __name__ == "__main__":
    main()
