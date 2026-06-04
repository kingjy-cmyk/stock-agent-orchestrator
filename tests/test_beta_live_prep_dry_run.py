import unittest

from stock_agent_orchestrator.services.beta_live_prep_dry_run import (
    beta_live_prep_dry_run_to_markdown,
    run_beta_live_prep_dry_run,
)


class BetaLivePrepDryRunTests(unittest.TestCase):
    def test_dry_run_passes_local_beta_live_preparation_chain(self) -> None:
        report = run_beta_live_prep_dry_run(callback_url="https://agent-beta.example.com")

        self.assertTrue(report.ok)
        self.assertTrue(report.config_written)
        self.assertTrue(report.config_ready)
        self.assertTrue(report.preflight_ok)
        self.assertTrue(report.runbook_ready)

    def test_markdown_does_not_render_fake_secrets(self) -> None:
        report = run_beta_live_prep_dry_run(callback_url="https://agent-beta.example.com")

        rendered = beta_live_prep_dry_run_to_markdown(report)

        self.assertIn("Beta Live Prep Dry Run", rendered)
        self.assertNotIn("dry-run-secret", rendered)
        self.assertNotIn("dry-run-token", rendered)
        self.assertNotIn("dry-run-encrypt-key", rendered)


if __name__ == "__main__":
    unittest.main()
