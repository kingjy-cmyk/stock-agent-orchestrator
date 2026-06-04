import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient, FeishuOperationError
from stock_agent_orchestrator.connectors.feishu_webhook import FeishuWebhookGateway, parse_message_event
from stock_agent_orchestrator.persistence.gateway_state_store import SQLiteGatewayStateStore
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue


def payload(text: str = "@小C-beta 今天先给我一份候选池", *, event_id: str = "evt-1", message_id: str = "msg-1") -> dict:
    return {
        "token": "verify-token",
        "event_id": event_id,
        "event": {
            "sender": {"sender_id": {"open_id": "user-open-id"}},
            "message": {
                "message_id": message_id,
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

    def test_verification_token_rejects_untrusted_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gateway = FeishuWebhookGateway(worker=self._worker(tmp), verification_token="verify-token")
            bad_payload = payload()
            bad_payload["token"] = "wrong"

            result = gateway.handle_payload(bad_payload, drain=True)

            self.assertFalse(result.accepted)
            self.assertEqual(result.reason, "invalid_verification_token")
            self.assertEqual(gateway.state_snapshot().status, "degraded")

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

    def test_duplicate_event_is_accepted_but_not_enqueued_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeFeishuClient()
            gateway = FeishuWebhookGateway(worker=self._worker(tmp, client))

            first = gateway.handle_payload(payload(), drain=True)
            second = gateway.handle_payload(payload(), drain=True)

            self.assertTrue(first.enqueued)
            self.assertTrue(second.accepted)
            self.assertFalse(second.enqueued)
            self.assertEqual(second.reason, "duplicate_event")
            self.assertEqual(len(client.sent_messages), 1)
            self.assertEqual(gateway.state_snapshot().duplicate_count, 1)

    def test_rate_limited_event_is_accepted_but_not_enqueued(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            now = 1000.0
            client = FakeFeishuClient()
            gateway = FeishuWebhookGateway(
                worker=self._worker(tmp, client),
                rate_limit_per_minute=1,
                clock=lambda: now,
            )

            first = gateway.handle_payload(payload(event_id="evt-1", message_id="msg-1"), drain=True)
            second = gateway.handle_payload(payload(event_id="evt-2", message_id="msg-2"), drain=True)

            self.assertTrue(first.enqueued)
            self.assertTrue(second.accepted)
            self.assertFalse(second.enqueued)
            self.assertEqual(second.reason, "rate_limited")
            self.assertEqual(len(client.sent_messages), 1)
            self.assertEqual(gateway.state_snapshot().rate_limited_count, 1)

    def test_rate_limit_window_expires(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            current_time = [1000.0]
            client = FakeFeishuClient()
            gateway = FeishuWebhookGateway(
                worker=self._worker(tmp, client),
                rate_limit_per_minute=1,
                clock=lambda: current_time[0],
            )

            first = gateway.handle_payload(payload(event_id="evt-1", message_id="msg-1"), drain=True)
            current_time[0] += 61.0
            second = gateway.handle_payload(payload(event_id="evt-2", message_id="msg-2"), drain=True)

            self.assertTrue(first.enqueued)
            self.assertTrue(second.enqueued)
            self.assertEqual(gateway.state_snapshot().rate_limited_count, 0)
            self.assertEqual(len(client.sent_messages), 2)

    def test_persistent_dedupe_survives_gateway_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "beta.db"
            first_client = FakeFeishuClient()
            first_gateway = FeishuWebhookGateway(
                worker=self._worker(tmp, first_client),
                state_store=SQLiteGatewayStateStore(db_path),
            )

            first = first_gateway.handle_payload(payload(), drain=True)

            second_client = FakeFeishuClient()
            second_gateway = FeishuWebhookGateway(
                worker=self._worker(tmp, second_client),
                state_store=SQLiteGatewayStateStore(db_path),
            )
            second = second_gateway.handle_payload(payload(), drain=True)

            self.assertTrue(first.enqueued)
            self.assertTrue(second.accepted)
            self.assertFalse(second.enqueued)
            self.assertEqual(second.reason, "duplicate_event")
            self.assertEqual(len(first_client.sent_messages), 1)
            self.assertEqual(len(second_client.sent_messages), 0)
            snapshot = second_gateway.state_snapshot()
            self.assertEqual(snapshot.accepted_count, 2)
            self.assertEqual(snapshot.enqueued_count, 1)
            self.assertEqual(snapshot.duplicate_count, 1)

    def test_persistent_operation_errors_survive_gateway_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "beta.db"
            gateway = FeishuWebhookGateway(
                worker=self._worker(tmp),
                state_store=SQLiteGatewayStateStore(db_path),
            )
            gateway.record_operation_error(
                FeishuOperationError(
                    kind="send_card",
                    chat_id="replace-me",
                    task_id="BETA-0001",
                    message="send failed",
                )
            )

            restarted = FeishuWebhookGateway(
                worker=self._worker(tmp),
                state_store=SQLiteGatewayStateStore(db_path),
            )

            self.assertEqual(restarted.state_snapshot().operation_error_count, 1)
            self.assertEqual(restarted.state_snapshot().status, "degraded")
            self.assertEqual(restarted.operation_errors()[0].task_id, "BETA-0001")

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
