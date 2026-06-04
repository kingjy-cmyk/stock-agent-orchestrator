import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.beta_live_launch_packet import (
    beta_live_launch_packet_to_markdown,
    build_beta_live_launch_packet,
)


class BetaLiveLaunchPacketTests(unittest.TestCase):
    def test_launch_packet_blocks_when_preflight_fails(self) -> None:
        packet = build_beta_live_launch_packet(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            repo_root=Path("."),
            config_path="configs/beta.live.example.toml",
        )

        self.assertFalse(packet.ready_to_launch)
        self.assertFalse(packet.preflight_ok)
        self.assertEqual(packet.stage, "fix_preflight_before_launch_packet")
        self.assertFalse(any("--allow-live-send" in command for command in packet.commands))
        self.assertTrue(any("ready_to_launch 为 false" in item for item in packet.stop_conditions))

    def test_launch_packet_outputs_beta_execution_packet_when_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "beta.live.toml"
            config_path.write_text(self._valid_config(), encoding="utf-8")

            packet = build_beta_live_launch_packet(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                repo_root=Path("."),
                config_path=str(config_path),
            )

            self.assertTrue(packet.ready_to_launch)
            self.assertEqual(packet.stage, "ready_to_execute_beta_launch")
            self.assertTrue(packet.beta_group_isolated)
            self.assertEqual(packet.feishu_console_values["callback_url"], "https://agent-beta.example.com/webhook")
            self.assertTrue(any("@xiaoc-beta" in item for item in packet.test_messages))
            self.assertTrue(any("collect-beta-evidence" in command for command in packet.commands))

    def test_markdown_does_not_render_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "beta.live.toml"
            config_path.write_text(self._valid_config(), encoding="utf-8")

            packet = build_beta_live_launch_packet(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                repo_root=Path("."),
                config_path=str(config_path),
            )

            rendered = beta_live_launch_packet_to_markdown(packet)

            self.assertIn("飞书 Beta Live Launch Packet", rendered)
            self.assertNotIn("real-secret-placeholder-for-test", rendered)
            self.assertNotIn("verify-token", rendered)
            self.assertNotIn("encrypt-key", rendered)

    def _valid_config(self) -> str:
        return """
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
api_base_url = "https://open.feishu.cn"
app_id = "cli_a_real_app"
app_secret = "real-secret-placeholder-for-test"
send_allowlist = ["oc_beta_chat"]
verification_token = "verify-token"
encrypt_key = "encrypt-key"
webhook_rate_limit_per_minute = 60
"""


if __name__ == "__main__":
    unittest.main()
