import unittest

from stock_agent_orchestrator.domain.models import AgentRole, TaskIntent, TaskStatus
from stock_agent_orchestrator.services.task_engine import TaskEngine


class TaskEngineTests(unittest.TestCase):
    def test_single_stock_research_progresses_to_waiting_user_for_rule_update(self) -> None:
        engine = TaskEngine()
        task = engine.create_task(
            task_id="TASK-1001",
            title="Research 600809",
            intent=TaskIntent.SINGLE_STOCK_RESEARCH,
        )

        self.assertEqual(task.status, TaskStatus.PLANNED)
        self.assertEqual(task.current_assignee, AgentRole.XIAOC)

        task = engine.advance_task(task, actor=AgentRole.XIAOC, message="delegated to xiaozhi")
        self.assertEqual(task.status, TaskStatus.ENRICHING)
        self.assertEqual(task.current_assignee, AgentRole.XIAOZHI)

        task = engine.advance_task(task, actor=AgentRole.XIAOZHI, message="seven-layer ready")
        self.assertEqual(task.status, TaskStatus.ANALYZING)
        self.assertEqual(task.current_assignee, AgentRole.XIAOBA)

        task = engine.advance_task(task, actor=AgentRole.XIAOBA, message="analysis complete")
        self.assertEqual(task.status, TaskStatus.FOLLOWING_UP)
        self.assertEqual(task.current_assignee, AgentRole.XIAOC)

        task = engine.advance_task(
            task,
            actor=AgentRole.XIAOC,
            message="new rule surfaced",
            within_known_rules=False,
        )
        self.assertEqual(task.status, TaskStatus.WAITING_USER)
        self.assertEqual(task.current_assignee, AgentRole.USER)

        task = engine.resume_from_user(task, "approved after review")
        self.assertEqual(task.status, TaskStatus.RECORDED)

    def test_daily_candidate_pool_can_auto_close_within_rules(self) -> None:
        engine = TaskEngine()
        task = engine.create_task(
            task_id="TASK-1002",
            title="Daily pool",
            intent=TaskIntent.DAILY_CANDIDATE_POOL,
        )
        task = engine.advance_task(task, actor=AgentRole.XIAOC, message="planned")
        task = engine.advance_task(task, actor=AgentRole.XIAOBA, message="candidate pool ready")
        task = engine.advance_task(task, actor=AgentRole.XIAOC, message="recorded")
        task = engine.advance_task(task, actor=AgentRole.XIAOC, message="closed")

        self.assertEqual(task.status, TaskStatus.CLOSED)


if __name__ == "__main__":
    unittest.main()
