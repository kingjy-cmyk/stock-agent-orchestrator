import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_config_review import (
    beta_live_config_review_to_markdown,
    build_beta_live_config_review,
)


class BetaLiveConfigReviewTests(unittest.TestCase):
    def test_review_reports_missing_config_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            review = build_beta_live_config_review(
                repo_root=root,
                config_path=root / "configs" / "beta.live.toml",
                callback_url="https://agent-beta.example.com",
            )

            self.assertFalse(review.ok)
            self.assertEqual(review.stage, "create_real_beta_config")
            self.assertTrue(review.gitignored)
            self.assertFalse(review.ready_for_preflight)

    def test_review_passes_when_config_is_complete_and_gitignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            review = build_beta_live_config_review(
                repo_root=root,
                config_path=config_path,
                callback_url="https://agent-beta.example.com",
            )

            self.assertTrue(review.ok)
            self.assertEqual(review.stage, "ready_for_beta_live_readiness_bundle")
            self.assertTrue(review.sensitive_fields_redacted)
            self.assertTrue(any("beta-live-readiness-bundle" in command for command in review.commands))

    def test_review_treats_secret_placeholders_as_safe_but_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(Path("configs/beta.live.example.toml").read_text(encoding="utf-8"), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            review = build_beta_live_config_review(repo_root=root, config_path=config_path)

            self.assertFalse(review.ok)
            self.assertEqual(review.stage, "complete_real_beta_config")
            self.assertTrue(review.sensitive_fields_redacted)
            self.assertFalse(review.ready_for_preflight)

    def test_markdown_does_not_render_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")
            (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            review = build_beta_live_config_review(repo_root=root, config_path=config_path)
            rendered = beta_live_config_review_to_markdown(review)

            self.assertIn("飞书 Beta Live Config Review", rendered)
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
