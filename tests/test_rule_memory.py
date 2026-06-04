import unittest

from stock_agent_orchestrator.domain.models import AgentRole, TaskIntent
from stock_agent_orchestrator.services.rule_memory import RuleMemoryService
from stock_agent_orchestrator.services.task_engine import TaskEngine


class RuleMemoryTests(unittest.TestCase):
    def test_rule_memory_splits_known_and_novel_rule_signals(self) -> None:
        engine = TaskEngine()
        task = engine.create_task(
            task_id="TASK-3001",
            title="Research 600809",
            intent=TaskIntent.SINGLE_STOCK_RESEARCH,
        )
        task = engine.advance_task(task, actor=AgentRole.XIAOC, message="delegated")
        task = engine.advance_task(task, actor=AgentRole.XIAOZHI, message="缺少放量阳线，七层数据已补齐")
        task = engine.advance_task(task, actor=AgentRole.XIAOBA, message="发现新规则，当前口径未定义")

        suggestions = RuleMemoryService().suggest_updates(task)

        self.assertEqual(len(suggestions), 2)
        self.assertFalse(suggestions[0].requires_user_review)
        self.assertTrue(suggestions[1].requires_user_review)


if __name__ == "__main__":
    unittest.main()
