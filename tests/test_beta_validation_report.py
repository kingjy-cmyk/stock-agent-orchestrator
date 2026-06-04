import json
import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.domain.models import TaskIntent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_validation_report import (
    BetaValidationEvidence,
    beta_validation_report_to_markdown,
    build_beta_validation_report,
)
from stock_agent_orchestrator.services.task_engine import TaskEngine


class BetaValidationReportTests(unittest.TestCase):
    def test_example_config_report_fails_until_real_beta_evidence_exists(self) -> None:
        report = build_beta_validation_report(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            commit="test-commit",
        )

        self.assertFalse(report.ok)
        self.assertFalse(report.preflight_ok)
        self.assertFalse(report.task_found)
        self.assertFalse(report.healthz_ok)

    def test_report_passes_with_preflight_task_and_healthz_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "beta.live.toml"
            db_path = tmp_path / "beta.db"
            healthz_path = tmp_path / "healthz.json"
            config_path.write_text(self._valid_config(), encoding="utf-8")

            store = SQLiteTaskStore(db_path)
            store.init_db()
            task = TaskEngine().create_task(
                task_id="BETA-0001",
                title="Daily candidate pool",
                intent=TaskIntent.DAILY_CANDIDATE_POOL,
                summary="@小C-beta 今天先给我一份候选池",
            )
            store.save_task(task)
            healthz_path.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "gateway": {
                            "status": "connected",
                            "accepted_count": 1,
                            "enqueued_count": 1,
                            "duplicate_count": 0,
                            "operation_error_count": 0,
                            "last_error": "",
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = build_beta_validation_report(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                commit="test-commit",
                db_path=db_path,
                task_id="BETA-0001",
                healthz_json_path=healthz_path,
                evidence=BetaValidationEvidence(beta_group_name="Stock Agent Beta"),
            )

            self.assertTrue(report.ok)
            self.assertTrue(report.preflight_ok)
            self.assertTrue(report.task_found)
            self.assertTrue(report.healthz_ok)
            self.assertEqual(report.task_id, "BETA-0001")

    def test_markdown_report_renders_core_sections(self) -> None:
        report = build_beta_validation_report(
            config=load_config(Path("configs/beta.live.example.toml")),
            callback_url="https://agent-beta.example.com",
            commit="test-commit",
        )

        rendered = beta_validation_report_to_markdown(report)

        self.assertIn("飞书 Beta 验证报告", rendered)
        self.assertIn("验收状态", rendered)
        self.assertIn("下一步", rendered)

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
"""


if __name__ == "__main__":
    unittest.main()
