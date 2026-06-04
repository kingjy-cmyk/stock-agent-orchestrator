import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.application_readiness import (
    readiness_report_to_markdown,
    run_application_readiness,
)


class ApplicationReadinessTests(unittest.TestCase):
    def test_current_repo_is_application_ready_but_missing_beta_evidence(self) -> None:
        report = run_application_readiness(Path("."))

        self.assertEqual(report.score, 82)
        self.assertEqual(report.max_score, 100)
        self.assertEqual(report.band, "application_ready_but_needs_beta_evidence")
        self.assertTrue(any("BETA_VALIDATION_REPORT_ZH.md" in blocker for blocker in report.blockers))

    def test_repo_with_beta_validation_report_is_ready_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative_path in [
                "LICENSE",
                "pyproject.toml",
                "README.md",
                "docs/INTRO_ZH.md",
                "docs/INSTALL_ZH.md",
                "docs/PREREQUISITES_ZH.md",
                "docs/ROADMAP_ZH.md",
                "docs/DEMO_SCRIPT_ZH.md",
                "docs/BETA_LIVE_PREFLIGHT_ZH.md",
                "docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md",
                "src/stock_agent_orchestrator/connectors/feishu.py",
                "src/stock_agent_orchestrator/connectors/feishu_webhook.py",
                "src/stock_agent_orchestrator/connectors/feishu_http.py",
                "docs/CODEX_FEISHU_PARITY_ZH.md",
                "docs/APPLICATION_ZH.md",
                "docs/BETA_VALIDATION_REPORT_ZH.md",
                "tests/test_placeholder.py",
            ]:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok", encoding="utf-8")

            report = run_application_readiness(root)

            self.assertEqual(report.score, 100)
            self.assertEqual(report.band, "ready_with_evidence")
            self.assertEqual(report.blockers, [])

    def test_markdown_report_renders_score_and_blockers(self) -> None:
        report = run_application_readiness(Path("."))

        rendered = readiness_report_to_markdown(report)

        self.assertIn("Application Readiness", rendered)
        self.assertIn("score", rendered)
        self.assertIn("Blockers", rendered)


if __name__ == "__main__":
    unittest.main()
