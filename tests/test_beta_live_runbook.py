import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.beta_live_runbook import (
    beta_live_runbook_to_markdown,
    build_beta_live_runbook,
)


class BetaLiveRunbookTests(unittest.TestCase):
    def test_runbook_blocks_when_preflight_fails(self) -> None:
        runbook = build_beta_live_runbook(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            repo_root=Path("."),
            config_path="configs/beta.live.example.toml",
        )

        self.assertFalse(runbook.ready_to_start)
        self.assertEqual(runbook.stage, "fix_preflight_before_beta_group_run")
        self.assertFalse(any("--allow-live-send" in command for command in runbook.commands))
        self.assertTrue(any("preflight 未通过" in item for item in runbook.stop_conditions))

    def test_runbook_outputs_live_beta_sequence_when_preflight_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "beta.live.toml"
            config_path.write_text(self._valid_config(), encoding="utf-8")

            runbook = build_beta_live_runbook(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                repo_root=Path("."),
                config_path=str(config_path),
                db_path=".runtime/webhook.db",
                healthz_json_path=".runtime/healthz.json",
                report_path="docs/BETA_VALIDATION_REPORT_ZH.md",
            )

            self.assertTrue(runbook.ready_to_start)
            self.assertEqual(runbook.stage, "ready_for_beta_group_run")
            self.assertTrue(any("run-webhook" in command and "--allow-live-send" in command for command in runbook.commands))
            self.assertTrue(any("beta-callback-probe" in command for command in runbook.commands))
            self.assertTrue(any("collect-beta-evidence" in command for command in runbook.commands))
            self.assertTrue(any("任务卡" in item for item in runbook.evidence_to_collect))

    def test_markdown_contains_manual_steps_and_stop_conditions(self) -> None:
        runbook = build_beta_live_runbook(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            repo_root=Path("."),
            config_path="configs/beta.live.example.toml",
        )

        rendered = beta_live_runbook_to_markdown(runbook)

        self.assertIn("飞书 Beta Live Runbook", rendered)
        self.assertIn("Manual Steps", rendered)
        self.assertIn("Stop Conditions", rendered)
        self.assertIn("Evidence To Collect", rendered)

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
