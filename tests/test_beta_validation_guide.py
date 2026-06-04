import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.beta_validation_guide import (
    beta_validation_guide_to_markdown,
    build_beta_validation_guide,
)


class BetaValidationGuideTests(unittest.TestCase):
    def test_guide_blocks_live_beta_when_preflight_fails(self) -> None:
        guide = build_beta_validation_guide(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            repo_root=Path("."),
            config_path="configs/beta.live.example.toml",
        )

        self.assertFalse(guide.ready_for_live_beta)
        self.assertFalse(guide.preflight_ok)
        self.assertEqual(guide.stage, "fix_preflight_before_live_beta")
        self.assertFalse(any("--allow-live-send" in command for command in guide.commands))
        self.assertTrue(any("不要启动 --allow-live-send" in item for item in guide.checklist))

    def test_guide_outputs_live_beta_evidence_commands_when_preflight_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "beta.live.toml"
            config_path.write_text(self._valid_config(), encoding="utf-8")

            guide = build_beta_validation_guide(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                repo_root=Path("."),
                config_path=str(config_path),
                db_path=".runtime/beta-live.db",
                healthz_json_path=".runtime/healthz.json",
                report_path="docs/BETA_VALIDATION_REPORT_ZH.md",
            )

            self.assertTrue(guide.ready_for_live_beta)
            self.assertTrue(guide.preflight_ok)
            self.assertEqual(guide.stage, "run_live_beta_and_collect_evidence")
            self.assertIn("https://agent-beta.example.com/webhook", guide.webhook_url)
            self.assertTrue(any("collect-beta-evidence" in command for command in guide.commands))
            self.assertTrue(any("BETA_VALIDATION_REPORT_ZH.md" in command for command in guide.commands))

    def test_markdown_contains_checklist_commands_and_evidence(self) -> None:
        guide = build_beta_validation_guide(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            repo_root=Path("."),
            config_path="configs/beta.live.example.toml",
        )

        rendered = beta_validation_guide_to_markdown(guide)

        self.assertIn("飞书 Beta 验收向导", rendered)
        self.assertIn("检查清单", rendered)
        self.assertIn("建议命令", rendered)
        self.assertIn("需要收集的证据", rendered)

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
"""


if __name__ == "__main__":
    unittest.main()
