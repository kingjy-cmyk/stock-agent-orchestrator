import json
import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.domain.models import TaskStatus
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.shadow_replay import (
    ShadowReplayService,
    extract_relay_log_messages,
    report_to_markdown,
    write_shadow_messages_jsonl,
)


class ShadowReplayTests(unittest.TestCase):
    def test_shadow_replay_creates_task_and_detects_waiting_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "messages.jsonl"
            sample.write_text(
                "\n".join(
                    [
                        json.dumps({"sender_name": "BOOS", "text": "@小C 研究一下 600809 七层数据"}),
                        json.dumps({"sender_name": "小智", "text": "小智 七层数据已补齐"}),
                        json.dumps({"sender_name": "小巴", "text": "小巴 分析完成，但需要确认是否新增规则"}),
                    ]
                ),
                encoding="utf-8",
            )
            store = SQLiteTaskStore(Path(tmp) / "shadow.db")

            report = ShadowReplayService().replay_file(sample, store)

            self.assertEqual(report.imported_messages, 3)
            self.assertEqual(report.created_tasks, 1)
            self.assertEqual(report.advanced_events, 2)
            self.assertEqual(report.tasks[0]["status"], TaskStatus.WAITING_USER.value)
            self.assertEqual(report.findings[0].kind, "waiting_user")

    def test_shadow_replay_detects_silent_break(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "messages.txt"
            sample.write_text("@小C: 今天先给我一份候选池\n小C: 已建任务\n", encoding="utf-8")
            store = SQLiteTaskStore(Path(tmp) / "shadow.db")

            report = ShadowReplayService().replay_file(sample, store)
            markdown = report_to_markdown(report)

            self.assertIn("silent_break", markdown)
            self.assertEqual(report.findings[0].severity, "warning")

    def test_shadow_replay_merges_followup_commands_into_active_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "messages.jsonl"
            sample.write_text(
                "\n".join(
                    [
                        json.dumps({"sender_name": "BOOS", "text": "@小C 建立离线 Shadow Mode"}),
                        json.dumps({"sender_name": "BOOS", "text": "继续完善这个功能"}),
                        json.dumps({"sender_name": "小C", "text": "已补充 CLI"}),
                    ]
                ),
                encoding="utf-8",
            )
            store = SQLiteTaskStore(Path(tmp) / "shadow.db")

            report = ShadowReplayService().replay_file(sample, store)

            self.assertEqual(report.created_tasks, 1)
            self.assertEqual(report.advanced_events, 2)
            self.assertGreaterEqual(report.tasks[0]["event_count"], 5)

    def test_extract_relay_log_messages_sanitizes_actor_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "relay.log"
            log.write_text(
                '2026/06/04 01:54:18 surface action: surface=feishu:小C:chat:oc_xxx '
                'chat=oc_xxx actor=ou_bd0520ebd38cb4b8cae1f780677a95ae kind=surface.message.text '
                'message=om_xxx instance= thread= verdict=current reason= event=evt request= '
                'message_time=2026-06-03T17:54:16.786Z menu_time= card_lifecycle= text="@小C 研究一下七层数据"\n'
                '2026/06/04 01:55:18 surface action: surface=feishu:小C:chat:oc_xxx '
                'chat=oc_xxx actor=ou_116be0127b77068c571a2123f52c38c4 kind=surface.message.text '
                'message=om_yyy instance= thread= verdict=current reason= event=evt request= '
                'message_time=2026-06-03T17:55:16.786Z menu_time= card_lifecycle= text="\\xe4\\xb8\\x83\\xe5\\xb1\\x82\\xe6\\x95\\xb0\\xe6\\x8d\\xae\\xe5\\xb7\\xb2\\xe8\\xa1\\xa5\\xe9\\xbd\\x90"\n',
                encoding="utf-8",
            )
            output = Path(tmp) / "messages.jsonl"

            messages = extract_relay_log_messages(log)
            write_shadow_messages_jsonl(messages, output)

            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0].sender_name, "BOOS")
            self.assertEqual(messages[1].sender_name, "小智")
            self.assertEqual(messages[1].text, "七层数据已补齐")
            self.assertNotIn("ou_", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
