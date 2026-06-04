from __future__ import annotations

from stock_agent_orchestrator.domain.models import Task, TaskIntent
from stock_agent_orchestrator.schemas.research import RuleUpdateSuggestion


class RuleMemoryService:
    """Heuristic rule-memory layer for the first MVP."""

    def suggest_updates(self, task: Task) -> list[RuleUpdateSuggestion]:
        if task.intent != TaskIntent.SINGLE_STOCK_RESEARCH:
            return []

        text = "\n".join(event.message for event in task.events)
        suggestions: list[RuleUpdateSuggestion] = []

        if "放量阳线" in text and "缺" in text:
            suggestions.append(
                RuleUpdateSuggestion(
                    title="require-volume-confirmation",
                    description="Keep or reinforce the rule that low RSI without volume confirmation cannot auto-trigger a build position.",
                    requires_user_review=False,
                    evidence=[task.task_id],
                )
            )

        if "新规则" in text or "首次" in text or "未定义" in text:
            suggestions.append(
                RuleUpdateSuggestion(
                    title="novel-rule-review",
                    description="A new or undefined rule surfaced during research and should be reviewed by the user before activation.",
                    requires_user_review=True,
                    evidence=[task.task_id],
                )
            )

        return suggestions

