import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_final_gate import (
    beta_live_final_gate_to_markdown,
    build_beta_live_final_gate,
)


class BetaLiveFinalGateTests(unittest.TestCase):
    def test_final_gate_blocks_missing_real_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            gate = build_beta_live_final_gate(
                repo_root=root,
                config_path=root / "configs" / "beta.live.toml",
                callback_url="https://agent-beta.example.com",
            )

            self.assertFalse(gate.ok)
            self.assertEqual(gate.stage, "fix_beta_live_config_review")
            self.assertTrue(any(item["name"] == "config_review" and item["status"] == "fail" for item in gate.checks))
            self.assertTrue(any("beta-live-config-review" in command for command in gate.commands))

    def test_final_gate_passes_with_complete_config_and_public_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            gate = build_beta_live_final_gate(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
                task_id="beta-0099",
            )

            self.assertTrue(gate.ok)
            self.assertEqual(gate.stage, "ready_to_execute_real_beta_validation")
            self.assertEqual(gate.task_id, "BETA-0099")
            self.assertTrue(any("run-webhook" in command and "--allow-live-send" in command for command in gate.commands))
            self.assertTrue(any("beta-callback-probe" in command for command in gate.commands))
            self.assertTrue(any("collect-beta-evidence" in command for command in gate.commands))

    def test_markdown_does_not_render_real_config_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            gate = build_beta_live_final_gate(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
            )
            rendered = beta_live_final_gate_to_markdown(gate)

            self.assertIn("飞书 Beta Live Final Gate", rendered)
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
