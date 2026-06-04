from __future__ import annotations

from dataclasses import dataclass

from stock_agent_orchestrator.domain.models import AgentRole, TaskIntent, TaskStatus


@dataclass(frozen=True, slots=True)
class PipelineStep:
    status: TaskStatus
    assignee: AgentRole
    label: str


PIPELINES: dict[TaskIntent, tuple[PipelineStep, ...]] = {
    TaskIntent.DAILY_CANDIDATE_POOL: (
        PipelineStep(TaskStatus.PLANNED, AgentRole.XIAOC, "小C确认委托并拆任务"),
        PipelineStep(TaskStatus.SCANNING, AgentRole.XIAOBA, "小巴筛出每日候选池"),
        PipelineStep(TaskStatus.FOLLOWING_UP, AgentRole.XIAOC, "小C追办落盘与透明回执"),
        PipelineStep(TaskStatus.RECORDED, AgentRole.XIAOC, "候选池落盘"),
        PipelineStep(TaskStatus.CLOSED, AgentRole.XIAOC, "任务关闭"),
    ),
    TaskIntent.SINGLE_STOCK_RESEARCH: (
        PipelineStep(TaskStatus.PLANNED, AgentRole.XIAOC, "小C确认研究目标"),
        PipelineStep(TaskStatus.ENRICHING, AgentRole.XIAOZHI, "小智补全七层数据"),
        PipelineStep(TaskStatus.ANALYZING, AgentRole.XIAOBA, "小巴给出分析结论"),
        PipelineStep(TaskStatus.FOLLOWING_UP, AgentRole.XIAOC, "小C补问、追证据、收口"),
        PipelineStep(TaskStatus.RECORDED, AgentRole.XIAOC, "研究卡与结论落盘"),
        PipelineStep(TaskStatus.CLOSED, AgentRole.XIAOC, "任务关闭"),
    ),
    TaskIntent.RULE_UPDATE: (
        PipelineStep(TaskStatus.PLANNED, AgentRole.XIAOC, "小C整理规则变更来源"),
        PipelineStep(TaskStatus.ANALYZING, AgentRole.XIAOBA, "小巴给出规则含义或失效原因"),
        PipelineStep(TaskStatus.FOLLOWING_UP, AgentRole.XIAOC, "小C判断是否需要用户审阅"),
        PipelineStep(TaskStatus.RECORDED, AgentRole.XIAOC, "规则草案落盘"),
        PipelineStep(TaskStatus.CLOSED, AgentRole.XIAOC, "任务关闭"),
    ),
}

