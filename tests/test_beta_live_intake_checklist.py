import unittest

from stock_agent_orchestrator.services.beta_live_intake_checklist import (
    beta_live_intake_checklist_to_markdown,
    build_beta_live_intake_checklist,
)


class BetaLiveIntakeChecklistTests(unittest.TestCase):
    def test_checklist_covers_required_feishu_and_path_values(self) -> None:
        checklist = build_beta_live_intake_checklist()
        env_names = {item.env_name for item in checklist.items}

        self.assertTrue(checklist.ok)
        self.assertEqual(checklist.stage, "collect_real_feishu_beta_values")
        self.assertIn("FEISHU_GROUP_CHAT_ID", env_names)
        self.assertIn("FEISHU_APP_SECRET", env_names)
        self.assertIn("FEISHU_VERIFICATION_TOKEN", env_names)
        self.assertIn("FEISHU_ENCRYPT_KEY", env_names)
        self.assertIn("STOCK_AGENT_SQLITE_DB", env_names)

    def test_checklist_marks_secrets_sensitive(self) -> None:
        checklist = build_beta_live_intake_checklist()
        sensitive = {item.env_name for item in checklist.items if item.sensitive}

        self.assertEqual(
            sensitive,
            {"FEISHU_APP_SECRET", "FEISHU_VERIFICATION_TOKEN", "FEISHU_ENCRYPT_KEY"},
        )

    def test_markdown_renders_commands_without_secret_values(self) -> None:
        checklist = build_beta_live_intake_checklist(shell="bash")
        rendered = beta_live_intake_checklist_to_markdown(checklist)

        self.assertIn("飞书 Beta Live Intake Checklist", rendered)
        self.assertIn("beta-live-env-template --shell bash", rendered)
        self.assertIn("FEISHU_APP_SECRET", rendered)
        self.assertNotIn("rehearsal-secret", rendered)
        self.assertNotIn("real-secret", rendered)

    def test_rejects_unknown_shell(self) -> None:
        with self.assertRaises(ValueError):
            build_beta_live_intake_checklist(shell="fish")


if __name__ == "__main__":
    unittest.main()
