import unittest

from stock_agent_orchestrator.services.beta_live_handoff import (
    beta_live_handoff_to_markdown,
    build_beta_live_handoff,
)


class BetaLiveHandoffTests(unittest.TestCase):
    def test_handoff_covers_approval_points_and_required_values(self) -> None:
        handoff = build_beta_live_handoff(callback_url="https://agent-beta.example.com")
        env_names = {item["env_name"] for item in handoff.required_values}

        self.assertTrue(handoff.ok)
        self.assertEqual(handoff.stage, "ready_to_collect_real_beta_inputs")
        self.assertIn("FEISHU_GROUP_CHAT_ID", env_names)
        self.assertIn("FEISHU_APP_SECRET", env_names)
        self.assertIn("FEISHU_VERIFICATION_TOKEN", env_names)
        self.assertTrue(any("临时 beta 群" in item for item in handoff.approval_points))

    def test_handoff_separates_safe_values_from_secrets(self) -> None:
        handoff = build_beta_live_handoff()

        self.assertIn("FEISHU_GROUP_CHAT_ID", handoff.safe_to_share)
        self.assertIn("FEISHU_APP_SECRET", handoff.secrets)
        self.assertIn("FEISHU_VERIFICATION_TOKEN", handoff.secrets)
        self.assertIn("FEISHU_ENCRYPT_KEY", handoff.secrets)
        self.assertNotIn("FEISHU_APP_SECRET", handoff.safe_to_share)

    def test_handoff_commands_end_at_final_gate(self) -> None:
        handoff = build_beta_live_handoff(
            callback_url="https://agent-beta.example.com",
            shell="bash",
            task_id="beta-0022",
        )

        self.assertEqual(handoff.shell, "bash")
        self.assertEqual(handoff.task_id, "BETA-0022")
        self.assertTrue(any("beta-live-env-template --shell bash" in command for command in handoff.commands))
        self.assertTrue(any("beta-live-final-gate" in command for command in handoff.commands))
        self.assertFalse(any("run-webhook" in command for command in handoff.commands))

    def test_markdown_does_not_render_secret_values(self) -> None:
        handoff = build_beta_live_handoff(callback_url="https://agent-beta.example.com")
        rendered = beta_live_handoff_to_markdown(handoff)

        self.assertIn("飞书 Beta Live Handoff", rendered)
        self.assertIn("FEISHU_APP_SECRET", rendered)
        self.assertNotIn("real-secret", rendered)
        self.assertNotIn("verify-token", rendered)
        self.assertNotIn("encrypt-key", rendered)


if __name__ == "__main__":
    unittest.main()
