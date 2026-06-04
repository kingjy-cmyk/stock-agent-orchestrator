import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_config_status import (
    beta_live_config_status_to_markdown,
    inspect_beta_live_config,
)


class BetaLiveConfigStatusTests(unittest.TestCase):
    def test_missing_config_reports_init_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            status = inspect_beta_live_config(config_path=tmp_path / "configs" / "beta.live.toml", repo_root=tmp_path)

            self.assertFalse(status.ok)
            self.assertFalse(status.exists)
            self.assertTrue(status.gitignored)
            self.assertTrue(any("init-beta-live-config" in step for step in status.next_steps))

    def test_placeholder_config_is_not_ready_for_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")
            config_path.write_text(Path("configs/beta.live.example.toml").read_text(encoding="utf-8"), encoding="utf-8")

            status = inspect_beta_live_config(config_path=config_path, repo_root=tmp_path)

            self.assertFalse(status.ok)
            self.assertTrue(status.exists)
            self.assertFalse(status.ready_for_preflight)
            self.assertTrue(any(item.status == "placeholder" for item in status.field_statuses))

    def test_complete_config_is_ready_and_redacts_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")
            config_path.write_text(self._valid_config(), encoding="utf-8")

            status = inspect_beta_live_config(config_path=config_path, repo_root=tmp_path)
            rendered = beta_live_config_status_to_markdown(status)

            self.assertTrue(status.ok)
            self.assertTrue(status.ready_for_preflight)
            self.assertNotIn("very-secret-value", rendered)
            self.assertNotIn("verify-token-secret", rendered)
            self.assertNotIn("encrypt-key-secret", rendered)
            self.assertIn("<redacted>", rendered)

    def test_config_must_be_gitignored_before_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "configs" / "beta.live.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self._valid_config(), encoding="utf-8")

            status = inspect_beta_live_config(config_path=config_path, repo_root=tmp_path)

            self.assertFalse(status.ok)
            self.assertFalse(status.gitignored)
            self.assertTrue(any(".gitignore" in step for step in status.next_steps))

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
app_secret = "very-secret-value"
send_allowlist = ["oc_beta_chat"]
verification_token = "verify-token-secret"
encrypt_key = "encrypt-key-secret"
webhook_rate_limit_per_minute = 60
"""


if __name__ == "__main__":
    unittest.main()
