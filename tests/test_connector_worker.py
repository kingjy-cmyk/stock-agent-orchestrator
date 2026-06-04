import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient, FeishuMessageEvent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue, IngressItem


def beta_event(message_id: str, text: str = "@小C-beta 今天先给我一份候选池") -> FeishuMessageEvent:
    return FeishuMessageEvent(
        event_id=f"evt-{message_id}",
        chat_id="replace-me",
        sender_open_id="user",
        sender_name="BOOS",
        text=text,
        mentions=("replace-me",),
        message_id=message_id,
    )


class ConnectorWorkerTests(unittest.TestCase):
    def test_worker_drains_ingress_and_sends_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            client = FakeFeishuClient()
            orchestrator = BetaOrchestratorService(
                config=config,
                store=SQLiteTaskStore(Path(tmp) / "beta.db"),
                feishu_client=client,
            )
            worker = ConnectorWorker(queue=BoundedIngressQueue(max_per_instance=8), orchestrator=orchestrator)
            worker.enqueue(IngressItem("beta", beta_event("m1")))
            worker.enqueue(IngressItem("beta", beta_event("m2", "测试")))

            report = worker.drain_once()

            self.assertEqual(report.processed, 2)
            self.assertEqual(report.handled, 1)
            self.assertEqual(report.ignored, 1)
            self.assertEqual(len(client.sent_messages), 1)
            self.assertIn("任务卡：BETA-0001", client.sent_messages[0].text)
            self.assertEqual(worker.stats("beta").current_depth, 0)


if __name__ == "__main__":
    unittest.main()
