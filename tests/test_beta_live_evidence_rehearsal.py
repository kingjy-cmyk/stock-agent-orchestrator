import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_evidence_rehearsal import (
    beta_live_evidence_rehearsal_to_markdown,
    run_beta_live_evidence_rehearsal,
)


class BetaLiveEvidenceRehearsalTests(unittest.TestCase):
    def test_rehearsal_writes_healthz_report_and_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rehearsal = run_beta_live_evidence_rehearsal(runtime_dir=Path(tmp))

            self.assertTrue(rehearsal.ok)
            self.assertEqual(rehearsal.task_id, "BETA-REHEARSAL-0001")
            self.assertTrue(Path(rehearsal.db_path).exists())
            self.assertTrue(Path(rehearsal.healthz_json_path).exists())
            self.assertTrue(Path(rehearsal.report_path).exists())
            self.assertTrue(any(item["name"] == "report_ok" and item["status"] == "pass" for item in rehearsal.checks))

    def test_rehearsal_report_is_marked_as_rehearsal_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rehearsal = run_beta_live_evidence_rehearsal(runtime_dir=Path(tmp))
            report = Path(rehearsal.report_path).read_text(encoding="utf-8")

            self.assertIn("本地彩排", report)
            self.assertIn("不能作为真实飞书 beta 申请证据", report)
            self.assertIn("om_rehearsal_task_card_1", report)

    def test_markdown_does_not_render_rehearsal_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rehearsal = run_beta_live_evidence_rehearsal(runtime_dir=Path(tmp))
            rendered = beta_live_evidence_rehearsal_to_markdown(rehearsal)

            self.assertIn("飞书 Beta Evidence Rehearsal", rendered)
            self.assertNotIn("rehearsal-secret", rendered)
            self.assertNotIn("rehearsal-token", rendered)
            self.assertNotIn("rehearsal-encrypt-key", rendered)


if __name__ == "__main__":
    unittest.main()
