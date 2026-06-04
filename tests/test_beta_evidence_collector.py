import json
import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.domain.models import TaskIntent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_evidence_collector import (
    beta_evidence_collection_to_markdown,
    collect_beta_evidence,
)
from stock_agent_orchestrator.services.beta_validation_report import BetaValidationEvidence
from stock_agent_orchestrator.services.task_engine import TaskEngine


class _FakeResponse:
    status = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class BetaEvidenceCollectorTests(unittest.TestCase):
    def test_collects_healthz_and_writes_validation_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "beta.live.toml"
            db_path = tmp_path / "beta.db"
            healthz_path = tmp_path / ".runtime" / "healthz.json"
            report_path = tmp_path / "docs" / "BETA_VALIDATION_REPORT_ZH.md"
            config_path.write_text(self._valid_config(), encoding="utf-8")
            self._write_beta_task(db_path)

            collection = collect_beta_evidence(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                commit="test-commit",
                db_path=db_path,
                healthz_json_path=healthz_path,
                report_path=report_path,
                evidence=BetaValidationEvidence(beta_group_name="Stock Agent Beta"),
                opener=lambda _request: _FakeResponse(
                    {"ok": True, "gateway": {"status": "connected", "operation_error_count": 0}}
                ),
            )

            self.assertTrue(collection.ok)
            self.assertEqual(collection.healthz_url, "https://agent-beta.example.com/healthz")
            self.assertTrue(healthz_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn("飞书 Beta 验证报告", report_path.read_text(encoding="utf-8"))
            self.assertIn("om_task_card_1", report_path.read_text(encoding="utf-8"))

    def test_collection_fails_but_still_writes_report_when_task_card_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "beta.live.toml"
            db_path = tmp_path / "beta.db"
            healthz_path = tmp_path / ".runtime" / "healthz.json"
            report_path = tmp_path / "docs" / "BETA_VALIDATION_REPORT_ZH.md"
            config_path.write_text(self._valid_config(), encoding="utf-8")
            store = SQLiteTaskStore(db_path)
            store.init_db()
            store.save_task(
                TaskEngine().create_task(
                    task_id="BETA-0001",
                    title="Daily candidate pool",
                    intent=TaskIntent.DAILY_CANDIDATE_POOL,
                    summary="@小C-beta 今天先给我一份候选池",
                )
            )

            collection = collect_beta_evidence(
                config=load_config(config_path),
                callback_url="https://agent-beta.example.com",
                commit="test-commit",
                db_path=db_path,
                healthz_json_path=healthz_path,
                report_path=report_path,
                opener=lambda _request: _FakeResponse(
                    {"ok": True, "gateway": {"status": "connected", "operation_error_count": 0}}
                ),
            )

            self.assertFalse(collection.ok)
            self.assertTrue(report_path.exists())
            self.assertIn("task_card_message_id", beta_evidence_collection_to_markdown(collection))

    def test_rejects_non_object_healthz_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "beta.live.toml"
            config_path.write_text(self._valid_config(), encoding="utf-8")

            with self.assertRaises(ValueError):
                collect_beta_evidence(
                    config=load_config(config_path),
                    callback_url="https://agent-beta.example.com",
                    commit="test-commit",
                    db_path=tmp_path / "beta.db",
                    healthz_json_path=tmp_path / ".runtime" / "healthz.json",
                    report_path=tmp_path / "docs" / "BETA_VALIDATION_REPORT_ZH.md",
                    opener=lambda _request: _FakeListResponse(),
                )

    def _write_beta_task(self, db_path: Path) -> None:
        store = SQLiteTaskStore(db_path)
        store.init_db()
        task = TaskEngine().create_task(
            task_id="BETA-0001",
            title="Daily candidate pool",
            intent=TaskIntent.DAILY_CANDIDATE_POOL,
            summary="@小C-beta 今天先给我一份候选池",
            context={
                "task_card_message_id": "om_task_card_1",
                "task_card_update_count": 1,
            },
        )
        store.save_task(task)

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


class _FakeListResponse(_FakeResponse):
    def __init__(self) -> None:
        self._payload = []

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
