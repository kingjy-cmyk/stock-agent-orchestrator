import tempfile
import unittest
from dataclasses import replace
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

    def test_agent_followup_updates_existing_task_instead_of_creating_new_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self._agent_config()
            store = SQLiteTaskStore(Path(tmp) / "beta.db")
            client = FakeFeishuClient()
            service = BetaOrchestratorService(config=config, store=store, feishu_client=client)

            created = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-1",
                    chat_id="replace-me",
                    sender_open_id="user-1",
                    sender_name="BOOS",
                    text="@小C-beta 今天先给我一份候选池",
                    mentions=("owner-open-id",),
                    message_id="msg-1",
                )
            )
            updated = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-2",
                    chat_id="replace-me",
                    sender_open_id="analyst-open-id",
                    sender_name="小巴-beta",
                    text="候选池已筛出，RSI<35 共 3 只",
                    mentions=(),
                    message_id="msg-2",
                )
            )

            self.assertTrue(created.handled)
            self.assertTrue(updated.handled)
            self.assertEqual(updated.task_id, "BETA-0001")
            self.assertEqual(len(store.list_tasks()), 1)
            task = store.load_task("BETA-0001")
            self.assertIsNotNone(task)
            self.assertEqual(task.status.value, "scanning")
            self.assertIn("候选池已筛出", client.sent_messages[-1].text)
            self.assertEqual(len(client.sent_messages), 2)

    def test_agent_followup_with_task_id_updates_that_task_not_latest_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self._agent_config()
            store = SQLiteTaskStore(Path(tmp) / "beta.db")
            client = FakeFeishuClient()
            service = BetaOrchestratorService(config=config, store=store, feishu_client=client)

            first = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-1",
                    chat_id="replace-me",
                    sender_open_id="user-1",
                    sender_name="BOOS",
                    text="@小C-beta 今天先给我一份候选池",
                    mentions=("owner-open-id",),
                    message_id="msg-1",
                )
            )
            second = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-2",
                    chat_id="replace-me",
                    sender_open_id="user-1",
                    sender_name="BOOS",
                    text="@小C-beta 研究一下贵州茅台七层数据",
                    mentions=("owner-open-id",),
                    message_id="msg-2",
                )
            )
            updated = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-3",
                    chat_id="replace-me",
                    sender_open_id="analyst-open-id",
                    sender_name="小巴-beta",
                    text="BETA-0001 候选池已筛出，RSI<35 共 3 只",
                    mentions=(),
                    message_id="msg-3",
                )
            )

            self.assertEqual(first.task_id, "BETA-0001")
            self.assertEqual(second.task_id, "BETA-0002")
            self.assertEqual(updated.task_id, "BETA-0001")
            task_1 = store.load_task("BETA-0001")
            task_2 = store.load_task("BETA-0002")
            self.assertIsNotNone(task_1)
            self.assertIsNotNone(task_2)
            self.assertEqual(task_1.status.value, "scanning")
            self.assertEqual(task_2.status.value, "planned")
            self.assertIn("任务卡：BETA-0001", client.sent_messages[-1].text)

    def test_agent_followup_with_unknown_task_id_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self._agent_config()
            store = SQLiteTaskStore(Path(tmp) / "beta.db")
            client = FakeFeishuClient()
            service = BetaOrchestratorService(config=config, store=store, feishu_client=client)

            result = service.process_message(
                FeishuMessageEvent(
                    event_id="evt-1",
                    chat_id="replace-me",
                    sender_open_id="analyst-open-id",
                    sender_name="小巴-beta",
                    text="BETA-9999 候选池已筛出",
                    mentions=(),
                    message_id="msg-1",
                )
            )

            self.assertFalse(result.handled)
            self.assertEqual(result.reason, "no_open_task")
            self.assertEqual(client.sent_messages, [])

    def _agent_config(self):
        config = load_config(Path("configs/beta.example.toml"))
        return replace(
            config,
            feishu=replace(
                config.feishu,
                owner_open_id="owner-open-id",
                data_open_id="data-open-id",
                analyst_open_id="analyst-open-id",
            ),
        )


if __name__ == "__main__":
    unittest.main()
