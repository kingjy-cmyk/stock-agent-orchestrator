import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient, FeishuMessageEvent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService


class BetaOrchestratorTests(unittest.TestCase):
    def test_beta_message_creates_task_and_sends_task_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            store = SQLiteTaskStore(Path(tmp) / "beta.db")
            client = FakeFeishuClient()
            service = BetaOrchestratorService(config=config, store=store, feishu_client=client)

            result = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-1",
                    chat_id="replace-me",
                    sender_open_id="user-1",
                    sender_name="BOOS",
                    text="@小C-beta 今天先给我一份候选池",
                    mentions=("replace-me",),
                    message_id="msg-1",
                )
            )

            self.assertTrue(result.handled)
            self.assertEqual(result.task_id, "BETA-0001")
            self.assertEqual(len(client.sent_messages), 1)
            self.assertIn("任务卡：BETA-0001", client.sent_messages[0].text)
            self.assertIn("当前责任人：小C", client.sent_messages[0].text)
            self.assertIsNotNone(store.load_task("BETA-0001"))

    def test_wrong_chat_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            client = FakeFeishuClient()
            service = BetaOrchestratorService(
                config=config,
                store=SQLiteTaskStore(Path(tmp) / "beta.db"),
                feishu_client=client,
            )

            result = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-2",
                    chat_id="other-chat",
                    sender_open_id="user-1",
                    sender_name="BOOS",
                    text="@小C-beta 今天先给我一份候选池",
                    mentions=("replace-me",),
                )
            )

            self.assertFalse(result.handled)
            self.assertEqual(result.reason, "chat_not_allowed")
            self.assertEqual(client.sent_messages, [])


if __name__ == "__main__":
    unittest.main()
