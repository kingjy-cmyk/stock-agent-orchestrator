from __future__ import annotations

from dataclasses import dataclass

from stock_agent_orchestrator.domain.models import TaskIntent


@dataclass(slots=True)
class ApprovalPolicy:
    auto_advance_within_rules: bool = True
    allow_real_trading: bool = False
    require_user_review_for_new_rules: bool = True

    def can_auto_advance(self, *, within_known_rules: bool, intent: TaskIntent) -> bool:
        if intent == TaskIntent.RULE_UPDATE and self.require_user_review_for_new_rules:
            return False
        return self.auto_advance_within_rules and within_known_rules

