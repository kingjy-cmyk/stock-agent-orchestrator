import unittest

from stock_agent_orchestrator.domain.models import AgentRole, TaskIntent, TaskStatus
from stock_agent_orchestrator.services.task_card import render_task_card_markdown
from stock_agent_orchestrator.services.task_engine import TaskEngine


class TaskCardTests(unittest.TestCase):
    def test_render_task_card_shows_status_assignee_and_approval(self) -> None:
        task = TaskEngine().create_task(
            task_id="TASK-2001",
            title="研究山西汾酒",
            intent=TaskIntent.SINGLE_STOCK_RESEARCH,
        )
        task.status = TaskStatus.WAITING_USER
        task.current_assignee = AgentRole.USER

        card = render_task_card_markdown(task)

        self.assertIn("任务卡：TASK-2001", card)
        self.assertIn("等待用户审批", card)
        self.assertIn("当前责任人：用户", card)
        self.assertIn("是否等待审批：是", card)


if __name__ == "__main__":
    unittest.main()
