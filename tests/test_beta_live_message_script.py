import unittest

from stock_agent_orchestrator.services.beta_live_message_script import (
    beta_live_message_script_to_markdown,
    build_beta_live_message_script,
)


class BetaLiveMessageScriptTests(unittest.TestCase):
    def test_script_contains_three_ordered_beta_group_steps(self) -> None:
        script = build_beta_live_message_script(task_id="BETA-0042")

        self.assertTrue(script.ok)
        self.assertEqual(len(script.steps), 3)
        self.assertEqual([item.step for item in script.steps], [1, 2, 3])
        self.assertEqual(script.steps[0].sender, "BOOS")
        self.assertIn("BETA-0042", script.steps[1].message)
        self.assertIn("BETA-0042", script.steps[2].message)

    def test_script_acceptance_criteria_require_task_card_evidence(self) -> None:
        script = build_beta_live_message_script()

        self.assertTrue(any("task_card_message_id" in item for item in script.acceptance_criteria))
        self.assertTrue(any("task_card_update_count" in item for item in script.acceptance_criteria))
        self.assertTrue(any("operation_error_count" in item for item in script.acceptance_criteria))

    def test_markdown_contains_commands_and_stop_conditions(self) -> None:
        script = build_beta_live_message_script(task_id="beta-0007")
        rendered = beta_live_message_script_to_markdown(script)

        self.assertIn("飞书 Beta Live Message Script", rendered)
        self.assertIn("BETA-0007", rendered)
        self.assertIn("Commands Before", rendered)
        self.assertIn("Commands After", rendered)
        self.assertIn("Stop Conditions", rendered)
        self.assertIn("collect-beta-evidence", rendered)


if __name__ == "__main__":
    unittest.main()
