import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient
from stock_agent_orchestrator.connectors.feishu_http import build_webhook_server
from stock_agent_orchestrator.services.beta_callback_probe import (
    callback_probe_report_to_markdown,
    run_beta_callback_probe,
)
from stock_agent_orchestrator.services.beta_validation_guide import build_beta_validation_guide


class BetaCallbackProbeTests(unittest.TestCase):
    def test_probe_checks_healthz_and_signed_challenge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            config = replace(
                config,
                feishu=replace(
                    config.feishu,
                    verification_token="verify-token",
                    encrypt_key="encrypt-key",
                ),
            )
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=config,
                db_path=Path(tmp) / "beta.db",
                feishu_client=FakeFeishuClient(),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                report = run_beta_callback_probe(
                    config=config,
                    callback_url=f"http://127.0.0.1:{server.server_address[1]}",
                    challenge="probe-challenge",
                )

                self.assertTrue(report.ok)
                self.assertEqual(report.challenge_response["challenge"], "probe-challenge")
                self.assertTrue(any(check.name == "healthz_gateway_status" and check.status == "pass" for check in report.checks))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_probe_fails_when_callback_is_unreachable(self) -> None:
        config = load_config(Path("configs/beta.example.toml"))

        report = run_beta_callback_probe(config=config, callback_url="http://127.0.0.1:1")

        self.assertFalse(report.ok)
        self.assertTrue(any(check.status == "fail" for check in report.checks))

    def test_markdown_report_contains_probe_sections(self) -> None:
        config = load_config(Path("configs/beta.example.toml"))
        report = run_beta_callback_probe(config=config, callback_url="")

        rendered = callback_probe_report_to_markdown(report)

        self.assertIn("Feishu Beta Callback Probe", rendered)
        self.assertIn("Checks", rendered)
        self.assertIn("Next Steps", rendered)

    def test_validation_guide_includes_callback_probe_after_preflight_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "beta.live.toml"
            config_path.write_text(self._valid_config(), encoding="utf-8")
            guide = build_beta_validation_guide(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                repo_root=Path("."),
                config_path=str(config_path),
            )

            self.assertTrue(guide.ready_for_live_beta)
            self.assertTrue(any("beta-callback-probe" in command for command in guide.commands))

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
