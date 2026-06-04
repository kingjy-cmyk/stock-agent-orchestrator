from __future__ import annotations

from stock_agent_orchestrator.domain.models import AgentRole, Task, TaskStatus


ROLE_LABELS = {
    AgentRole.XIAOC: "小C",
    AgentRole.XIAOZHI: "小智",
    AgentRole.XIAOBA: "小巴",
    AgentRole.USER: "用户",
    AgentRole.SYSTEM: "系统",
}

STATUS_LABELS = {
    TaskStatus.NEW: "新建",
    TaskStatus.PLANNED: "已规划",
    TaskStatus.SCANNING: "筛选中",
    TaskStatus.ENRICHING: "补数据",
    TaskStatus.ANALYZING: "分析中",
    TaskStatus.FOLLOWING_UP: "追办中",
    TaskStatus.WAITING_USER: "等待用户审批",
    TaskStatus.RECORDED: "已落盘",
    TaskStatus.CLOSED: "已关闭",
}


def render_task_card_markdown(task: Task) -> str:
    evidence = "\n".join(f"- {artifact.kind}: {artifact.summary or artifact.path}" for artifact in task.artifacts)
    if not evidence:
        evidence = "- 暂无证据产物"

    next_action = "等待当前责任人继续推进"
    if task.status == TaskStatus.WAITING_USER:
        next_action = "等待用户审批或补充边界"
    elif task.status in {TaskStatus.RECORDED, TaskStatus.CLOSED}:
        next_action = "检查证据后归档"

    return "\n".join(
        [
            f"## 任务卡：{task.task_id}",
            "",
            f"- 目标：{task.title}",
            f"- 意图：{task.intent.value}",
            f"- 状态：{STATUS_LABELS[task.status]} `{task.status.value}`",
            f"- 当前责任人：{ROLE_LABELS[task.current_assignee]}",
            f"- 下一步：{next_action}",
            f"- 是否等待审批：{'是' if task.status == TaskStatus.WAITING_USER else '否'}",
            "",
            "### 证据",
            evidence,
            "",
            "### 最近事件",
            *recent_event_lines(task),
        ]
    )


def recent_event_lines(task: Task, *, limit: int = 5) -> list[str]:
    events = task.events[-limit:]
    if not events:
        return ["- 暂无事件"]
    return [f"- {ROLE_LABELS[event.actor]}: {event.message}" for event in events]
