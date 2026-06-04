import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_control_panel import (
    beta_live_control_panel_to_markdown,
    build_beta_live_control_panel,
)


class BetaLiveControlPanelTests(unittest.TestCase):
    def test_panel_points_to_config_collection_when_real_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            panel = build_beta_live_control_panel(
                repo_root=root,
                config_path=root / "configs" / "beta.live.toml",
                callback_url="https://agent-beta.example.com",
            )

            self.assertFalse(panel.ok)
            self.assertEqual(panel.stage, "collect_or_fix_real_beta_config")
            self.assertEqual(panel.next_action, "fill_or_review_configs_beta_live_toml")
            self.assertTrue(any("beta-live-handoff" in command for command in panel.commands))

    def test_panel_reaches_ready_to_start_when_all_local_gates_pass_and_report_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            panel = build_beta_live_control_panel(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
                task_id="beta-0042",
            )

            self.assertTrue(panel.ok)
            self.assertEqual(panel.stage, "ready_to_start_real_beta_execution")
            self.assertEqual(panel.task_id, "BETA-0042")
            self.assertTrue(any("run-webhook" in command for command in panel.commands))
            self.assertTrue(any("collect-beta-evidence" in command for command in panel.commands))

    def test_panel_detects_existing_real_beta_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "docs" / "BETA_VALIDATION_REPORT_ZH.md"
            report_path.parent.mkdir(parents=True)
            report_path.write_text("# report\n", encoding="utf-8")

            panel = build_beta_live_control_panel(
                repo_root=root,
                config_path=root / "configs" / "beta.live.toml",
                callback_url="https://agent-beta.example.com",
                report_path="docs/BETA_VALIDATION_REPORT_ZH.md",
            )

            self.assertTrue(panel.ok)
            self.assertEqual(panel.stage, "real_beta_evidence_present")
            self.assertTrue(any("application-readiness" in command for command in panel.commands))

    def test_markdown_does_not_render_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            panel = build_beta_live_control_panel(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
            )
            rendered = beta_live_control_panel_to_markdown(panel)

            self.assertIn("飞书 Beta Live Control Panel", rendered)
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
