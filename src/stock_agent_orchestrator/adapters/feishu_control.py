from __future__ import annotations

from dataclasses import dataclass

from stock_agent_orchestrator.domain.models import TaskIntent


@dataclass(slots=True)
class FeishuEnvelope:
    sender_name: str
    text: str
    mentions_owner: bool = False


@dataclass(slots=True)
class TaskCommand:
    title: str
    intent: TaskIntent
    auto_within_rules: bool
    raw_text: str


class FeishuControlAdapter:
    def parse(self, envelope: FeishuEnvelope) -> TaskCommand | None:
        if envelope.sender_name.strip() in {"小C", "小智", "小巴"}:
            return None

        if not envelope.mentions_owner:
            return None

        text = envelope.text.strip()
        if not text:
            return None
        if not self._looks_like_delegation(text):
            return None

        intent = self._detect_intent(text)
        title = self._build_title(intent, text)
        auto_within_rules = "按现有规则" in text or "按当前规则" in text or "去做" in text
        return TaskCommand(title=title, intent=intent, auto_within_rules=auto_within_rules, raw_text=text)

    def _detect_intent(self, text: str) -> TaskIntent:
        if "规则" in text or "复盘" in text or "总结" in text:
            return TaskIntent.RULE_UPDATE
        if "七层" in text or "研究" in text or "单票" in text:
            return TaskIntent.SINGLE_STOCK_RESEARCH
        return TaskIntent.DAILY_CANDIDATE_POOL

    def _build_title(self, intent: TaskIntent, text: str) -> str:
        prefix = {
            TaskIntent.DAILY_CANDIDATE_POOL: "Daily candidate pool",
            TaskIntent.SINGLE_STOCK_RESEARCH: "Single stock research",
            TaskIntent.RULE_UPDATE: "Rule and memory update",
        }[intent]
        short = text.replace("\n", " ").strip()
        if len(short) > 48:
            short = short[:47] + "…"
        return f"{prefix}: {short}"

    def _looks_like_delegation(self, text: str) -> bool:
        lowered = text.lower()
        if text in {"1", "测试", "能收到吗", "能收到吗？", "现在能收到吧"}:
            return False
        keywords = (
            "帮我",
            "给我",
            "研究",
            "分析",
            "检查",
            "修复",
            "申请",
            "建立",
            "开发",
            "实现",
            "设置",
            "选股",
            "候选",
            "七层",
            "复盘",
            "总结",
            "完善",
            "推进",
            "落地",
            "shadow",
            "codex",
            "repo",
            "github",
        )
        return any(keyword in text or keyword in lowered for keyword in keywords)
