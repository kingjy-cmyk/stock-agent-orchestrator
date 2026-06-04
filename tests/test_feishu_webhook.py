import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient
from stock_agent_orchestrator.connectors.feishu_webhook import FeishuWebhookGateway, parse_message_event
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue


def payload(text: str = "@小C-beta 今天先给我一份候选池") -> dict:
    return {
        "event_id": "evt-1",
        "event": {
            "sender": {"sender_id": {"open_id": "user-open-id"}},
            "message": {
                "message_id": "msg-1",
                "chat_id": "replace-me",
                "chat_type": "group",
                "content": f'{{"text":"{text}"}}',
                "mentions": [{"id": {"open_id": "replace-me"}, "name": "小C-beta"}],
                "create_time": "1780581200",
            },
        },
    }


class FeishuWebhookTests(unittest.TestCase):
    def test_challenge_payload_is_accepted_without_enqueue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gateway = FeishuWebhookGateway(worker=self._worker(tmp))

            result = gateway.handle_payload({"challenge": "abc"})

            self.assertTrue(result.accepted)
            self.assertFalse(result.enqueued)
            self.assertEqual(result.challenge, "abc")

    def test_parse_message_event_extracts_text_chat_sender_and_mentions(self) -> None:
        event = parse_message_event(payload())

        self.assertIsNotNone(event)
        self.assertEqual(event.chat_id, "replace-me")
        self.assertEqual(event.text, "@小C-beta 今天先给我一份候选池")
        self.assertEqual(event.sender_open_id, "user-open-id")
        self.assertEqual(event.mentions, ("replace-me",))

    def test_webhook_gateway_enqueues_and_drains_to_task_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeFeishuClient()
            gateway = FeishuWebhookGateway(worker=self._worker(tmp, client))

            result = gateway.handle_payload(payload(), drain=True)

            self.assertTrue(result.accepted)
            self.assertTrue(result.enqueued)
            self.assertIsNotNone(result.worker_report)
            self.assertEqual(result.worker_report.handled, 1)
            self.assertEqual(len(client.sent_messages), 1)
            self.assertIn("任务卡：BETA-0001", client.sent_messages[0].text)

    def _worker(self, tmp, client=None) -> ConnectorWorker:
        if hasattr(tmp, "name"):
            tmp_path = Path(tmp.name)
        else:
            tmp_path = Path(tmp)
        config = load_config(Path("configs/beta.example.toml"))
        client = client or FakeFeishuClient()
        return ConnectorWorker(
            queue=BoundedIngressQueue(max_per_instance=8),
            orchestrator=BetaOrchestratorService(
                config=config,
                store=SQLiteTaskStore(tmp_path / "beta.db"),
                feishu_client=client,
            ),
        )


if __name__ == "__main__":
    unittest.main()
