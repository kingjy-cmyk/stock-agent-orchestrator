from __future__ import annotations

from pathlib import Path

from stock_agent_orchestrator.services.shadow_replay import ShadowMessage, write_shadow_messages_jsonl


DEMO_MESSAGES = (
    ShadowMessage("BOOS", "@小C 今天先给我一份候选池", "2026-06-04T09:00:00Z", True),
    ShadowMessage("小C", "已建任务，交给小巴筛候选池", "2026-06-04T09:01:00Z", False),
    ShadowMessage("小巴", "候选池已完成，但没有看到落盘证据", "2026-06-04T09:05:00Z", False),
    ShadowMessage("BOOS", "继续完善这个闭环", "2026-06-04T09:06:00Z", True),
)


def write_demo_sample(output_path: Path) -> Path:
    write_shadow_messages_jsonl(DEMO_MESSAGES, output_path)
    return output_path
