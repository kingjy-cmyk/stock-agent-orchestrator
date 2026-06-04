import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config, validate_config


class ConfigTests(unittest.TestCase):
    def test_beta_example_loads_and_warns_on_placeholders(self) -> None:
        config = load_config(Path("configs/beta.example.toml"))

        issues = validate_config(config)

        self.assertEqual(config.project.environment, "beta")
        self.assertTrue(any(issue.severity == "warning" for issue in issues))
        self.assertFalse(any(issue.severity == "error" for issue in issues))

    def test_config_loader_accepts_utf8_bom_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
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
candidate_list = "./candidate_list.md"
seven_layer_reports = "./seven_layer"
entry_monitor_reports = "./monitor"
sqlite_db = "./runtime/beta.db"

[feishu]
group_chat_id = "chat"
owner_open_id = "owner"
data_open_id = "data"
analyst_open_id = "analyst"
""",
                encoding="utf-8-sig",
            )

            config = load_config(path)

            self.assertEqual(config.project.environment, "beta")

    def test_formal_active_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
[project]
name = "stock-agent-orchestrator"
environment = "formal"
mode = "active"

[roles]
owner = "xiaoc"
data = "xiaozhi"
analyst = "xiaoba"

[automation]
auto_advance_within_rules = true
allow_real_trading = false
require_user_review_for_new_rules = true

[paths]
candidate_list = "./candidate_list.md"
seven_layer_reports = "./seven_layer"
entry_monitor_reports = "./monitor"
sqlite_db = "./runtime/formal.db"

[feishu]
group_chat_id = "chat"
owner_open_id = "owner"
data_open_id = "data"
analyst_open_id = "analyst"
""",
                encoding="utf-8",
            )

            issues = validate_config(load_config(path))

            self.assertTrue(any(issue.severity == "error" and issue.field == "project.mode" for issue in issues))

    def test_live_send_requires_beta_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
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
candidate_list = "./candidate_list.md"
seven_layer_reports = "./seven_layer"
entry_monitor_reports = "./monitor"
sqlite_db = "./runtime/beta.db"

[feishu]
group_chat_id = "chat"
owner_open_id = "owner"
data_open_id = "data"
analyst_open_id = "analyst"
send_mode = "live"
send_allowlist = []
""",
                encoding="utf-8",
            )

            issues = validate_config(load_config(path))

            self.assertTrue(any(issue.severity == "error" and issue.field == "feishu.app_id" for issue in issues))
            self.assertTrue(any(issue.severity == "error" and issue.field == "feishu.send_allowlist" for issue in issues))
            self.assertTrue(any(issue.severity == "error" and issue.field == "feishu.verification_token" for issue in issues))

    def test_live_send_requires_group_in_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
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
candidate_list = "./candidate_list.md"
seven_layer_reports = "./seven_layer"
entry_monitor_reports = "./monitor"
sqlite_db = "./runtime/beta.db"

[feishu]
group_chat_id = "chat"
owner_open_id = "owner"
data_open_id = "data"
analyst_open_id = "analyst"
send_mode = "live"
app_id = "app"
app_secret = "secret"
send_allowlist = ["other-chat"]
verification_token = "token"
""",
                encoding="utf-8",
            )

            issues = validate_config(load_config(path))

            self.assertTrue(any(issue.severity == "error" and issue.field == "feishu.send_allowlist" for issue in issues))

    def test_live_example_rejects_placeholders(self) -> None:
        issues = validate_config(load_config(Path("configs/beta.live.example.toml")))

        self.assertTrue(any(issue.severity == "error" and issue.field == "feishu.app_id" for issue in issues))


if __name__ == "__main__":
    unittest.main()
