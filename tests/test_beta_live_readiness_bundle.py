import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_readiness_bundle import (
    beta_live_readiness_bundle_to_markdown,
    build_beta_live_readiness_bundle,
)


class BetaLiveReadinessBundleTests(unittest.TestCase):
    def test_bundle_reports_missing_real_config_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            bundle = build_beta_live_readiness_bundle(
                repo_root=root,
                config_path=root / "configs" / "beta.live.toml",
                callback_url="https://agent-beta.example.com",
            )

            self.assertFalse(bundle.ok)
            self.assertTrue(bundle.dry_run_ok)
            self.assertFalse(bundle.config_ready)
            self.assertEqual(bundle.stage, "fill_real_beta_config")
            self.assertIsNone(bundle.preflight)
            self.assertTrue(any(item["name"] == "config_status" and item["status"] == "fail" for item in bundle.checks))

    def test_bundle_reaches_ready_for_real_beta_when_config_is_ready_but_evidence_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            bundle = build_beta_live_readiness_bundle(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
            )

            self.assertTrue(bundle.ok)
            self.assertTrue(bundle.config_ready)
            self.assertTrue(bundle.preflight_ok)
            self.assertTrue(bundle.runbook_ready)
            self.assertTrue(bundle.launch_ready)
            self.assertTrue(bundle.missing_real_beta_evidence)
            self.assertEqual(bundle.stage, "ready_for_real_beta_group_validation")
            self.assertIsNotNone(bundle.launch_packet)

    def test_markdown_does_not_render_real_config_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            bundle = build_beta_live_readiness_bundle(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
            )
            rendered = beta_live_readiness_bundle_to_markdown(bundle)

            self.assertIn("飞书 Beta Live Readiness Bundle", rendered)
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
