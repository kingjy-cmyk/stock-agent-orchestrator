import json
import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.domain.models import TaskStatus
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.shadow_replay import ShadowReplayService, report_to_markdown


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


if __name__ == "__main__":
    unittest.main()
