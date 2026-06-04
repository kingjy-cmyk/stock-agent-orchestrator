import unittest

from stock_agent_orchestrator.services.beta_callback_deploy_plan import (
    beta_callback_deploy_plan_to_markdown,
    build_beta_callback_deploy_plan,
)


class BetaCallbackDeployPlanTests(unittest.TestCase):
    def test_plan_passes_for_public_https_callback(self) -> None:
        plan = build_beta_callback_deploy_plan(callback_url="https://agent-beta.example.com")

        self.assertTrue(plan.ok)
        self.assertEqual(plan.stage, "ready_to_start_callback_probe")
        self.assertEqual(plan.webhook_url, "https://agent-beta.example.com/webhook")
        self.assertEqual(plan.healthz_url, "https://agent-beta.example.com/healthz")
        self.assertTrue(any("run-webhook" in command for command in plan.commands))
        self.assertTrue(any("beta-callback-probe" in command for command in plan.commands))

    def test_plan_blocks_localhost_callback(self) -> None:
        plan = build_beta_callback_deploy_plan(callback_url="http://127.0.0.1:8787")

        self.assertFalse(plan.ok)
        self.assertEqual(plan.stage, "fix_callback_deploy_plan")
        self.assertFalse(plan.public_https)
        self.assertTrue(any(item["name"] == "callback_url_public_https" and item["status"] == "fail" for item in plan.checks))

    def test_plan_blocks_invalid_port(self) -> None:
        plan = build_beta_callback_deploy_plan(callback_url="https://agent-beta.example.com", port=70000)

        self.assertFalse(plan.ok)
        self.assertTrue(any(item["name"] == "port_valid" and item["status"] == "fail" for item in plan.checks))

    def test_markdown_contains_feishu_console_steps_and_evidence(self) -> None:
        plan = build_beta_callback_deploy_plan(callback_url="https://agent-beta.example.com")
        rendered = beta_callback_deploy_plan_to_markdown(plan)

        self.assertIn("飞书 Beta Callback Deploy Plan", rendered)
        self.assertIn("Feishu Console Steps", rendered)
        self.assertIn("Evidence To Collect", rendered)
        self.assertIn("https://agent-beta.example.com/webhook", rendered)


if __name__ == "__main__":
    unittest.main()
