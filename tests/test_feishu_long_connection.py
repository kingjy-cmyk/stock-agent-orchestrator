import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.connectors.feishu_long_connection import (
    build_long_connection_runtime_from_config,
    build_long_connection_runtime_status,
    _p2_message_event_to_payload,
)


class FeishuLongConnectionTests(unittest.TestCase):
    def test_long_connection_runtime_status_uses_long_connection_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "beta.live.toml"
            config_path.write_text(self._config(event_mode="long_connection"), encoding="utf-8")

            status = build_long_connection_runtime_status(config_path=config_path, db_path=root / "long.db")

            self.assertTrue(status.ok)
            self.assertEqual(status.event_mode, "long_connection")
            self.assertIn("accepted_count", status.state)
            self.assertTrue(any("Start run-long-connection" in item for item in status.next_steps))

    def test_long_connection_runtime_rejects_callback_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "beta.live.toml"
            config_path.write_text(self._config(event_mode="callback"), encoding="utf-8")

            with self.assertRaises(RuntimeError):
                build_long_connection_runtime_from_config(config_path=config_path, db_path=root / "long.db")

    def test_p2_message_event_is_converted_to_webhook_payload_shape(self) -> None:
        event = Obj(
            schema="2.0",
            header=Obj(event_id="evt-1", event_type="im.message.receive_v1"),
            event=Obj(
                sender=Obj(sender_id=Obj(open_id="ou_sender")),
                message=Obj(
                    message_id="om_1",
                    chat_id="oc_beta_chat",
                    create_time=1710000000000,
                    content='{"text":"beta ping"}',
                    mentions=[Obj(id=Obj(open_id="ou_owner"))],
                ),
            ),
        )

        payload = _p2_message_event_to_payload(event)

        self.assertEqual(payload["event_id"], "evt-1")
        self.assertEqual(payload["event"]["message"]["chat_id"], "oc_beta_chat")
        self.assertEqual(payload["event"]["sender"]["sender_id"]["open_id"], "ou_sender")
        self.assertEqual(payload["event"]["message"]["mentions"][0]["id"]["open_id"], "ou_owner")

    def test_customized_p2_message_event_preserves_sender_app_id(self) -> None:
        event = Obj(
            schema="2.0",
            header=Obj(event_id="evt-2", event_type="im.message.receive_v1"),
            event={
                "sender": {"sender_id": {"app_id": "cli_data"}, "sender_type": "app"},
                "message": {
                    "message_id": "om_2",
                    "chat_id": "oc_beta_chat",
                    "content": '{"text":"BETA-0001 七层数据已拉取"}',
                },
            },
        )

        payload = _p2_message_event_to_payload(event)

        self.assertEqual(payload["event"]["sender"]["sender_id"]["app_id"], "cli_data")

    def _config(self, *, event_mode: str) -> str:
        return f"""
[project]
name = "stock-agent-orchestrator"
environment = "beta"
mode = "active"

[roles]
owner = "xiaoc-beta"
data = "xiaozhi-beta"
analyst = "xiaoba-beta"

[automation]
auto_advance_within_rules = true
allow_real_trading = false
require_user_review_for_new_rules = true

[paths]
candidate_list = "./runtime/candidate_list.md"
seven_layer_reports = "./runtime/seven_layer"
entry_monitor_reports = "./runtime/entry_monitor"
sqlite_db = "./runtime/beta-live.db"

[feishu]
group_chat_id = "oc_beta_chat"
owner_open_id = "ou_owner"
data_open_id = "ou_data"
analyst_open_id = "ou_analyst"
send_mode = "live"
event_mode = "{event_mode}"
api_base_url = "https://open.feishu.cn"
app_id = "cli_a_real_app"
app_secret = "real-secret-placeholder-for-test"
send_allowlist = ["oc_beta_chat"]
verification_token = "verify-token"
encrypt_key = "encrypt-key"
webhook_rate_limit_per_minute = 60
"""


class Obj:
    def __init__(self, **values) -> None:
        self.__dict__.update(values)


if __name__ == "__main__":
    unittest.main()
