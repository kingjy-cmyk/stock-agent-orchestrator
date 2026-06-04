import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.beta_live_preflight import (
    preflight_report_to_markdown,
    run_beta_live_preflight,
)


class BetaLivePreflightTests(unittest.TestCase):
    def test_live_example_fails_until_placeholders_are_replaced(self) -> None:
        config = load_config(Path("configs/beta.live.example.toml"))

        report = run_beta_live_preflight(config, callback_url="https://agent-beta.example.com")

        self.assertFalse(report.ok)
        self.assertTrue(any(check.name == "config_validation" and check.status == "fail" for check in report.checks))
        self.assertTrue(any(check.name == "no_required_placeholders" and check.status == "fail" for check in report.checks))

    def test_valid_beta_live_shape_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "beta.live.toml"
            config_path.write_text(
                """
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
""",
                encoding="utf-8",
            )

            report = run_beta_live_preflight(load_config(config_path), callback_url="https://agent-beta.example.com")

            self.assertTrue(report.ok)
            self.assertEqual(report.webhook_url, "https://agent-beta.example.com/webhook")
            self.assertTrue(all(check.status == "pass" for check in report.checks))

    def test_callback_url_must_be_https(self) -> None:
        config = load_config(Path("configs/beta.live.example.toml"))

        report = run_beta_live_preflight(config, callback_url="http://127.0.0.1:8787")

        self.assertFalse(report.ok)
        self.assertTrue(any(check.name == "no_required_placeholders" and check.status == "fail" for check in report.checks))

    def test_long_connection_mode_does_not_require_public_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "beta.live.toml"
            config_path.write_text(
                self._long_connection_config(),
                encoding="utf-8",
            )

            report = run_beta_live_preflight(load_config(config_path), callback_url="")

            self.assertTrue(report.ok)
            self.assertEqual(report.event_mode, "long_connection")
            self.assertEqual(report.webhook_url, "")
            self.assertEqual(report.healthz_url, "/healthz")
            self.assertTrue(any(check.name == "long_connection_transport" and check.status == "pass" for check in report.checks))

    def test_markdown_report_contains_next_steps(self) -> None:
        config = load_config(Path("configs/beta.live.example.toml"))
        report = run_beta_live_preflight(config, callback_url="https://agent-beta.example.com")

        rendered = preflight_report_to_markdown(report)

        self.assertIn("Feishu Beta Live Preflight", rendered)
        self.assertIn("Next Steps", rendered)

    def _long_connection_config(self) -> str:
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
event_mode = "long_connection"
api_base_url = "https://open.feishu.cn"
app_id = "cli_a_real_app"
app_secret = "real-secret-placeholder-for-test"
send_allowlist = ["oc_beta_chat"]
verification_token = ""
encrypt_key = ""
webhook_rate_limit_per_minute = 60
"""


if __name__ == "__main__":
    unittest.main()
