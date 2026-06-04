from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from stock_agent_orchestrator.domain.models import (
    AgentRole,
    ArtifactRef,
    EventType,
    Task,
    TaskEvent,
    TaskIntent,
    TaskStatus,
)
from stock_agent_orchestrator.domain.policies import ApprovalPolicy
from stock_agent_orchestrator.services.pipeline import PIPELINES, PipelineStep


class TaskEngine:
    def __init__(self, policy: ApprovalPolicy | None = None) -> None:
        self.policy = policy or ApprovalPolicy()

    def create_task(
        self,
        *,
        task_id: str,
        title: str,
        intent: TaskIntent,
        summary: str = "",
        context: dict | None = None,
    ) -> Task:
        task = Task(
            task_id=task_id,
            title=title,
            intent=intent,
            summary=summary,
            context=context or {},
        )
        task.add_event(TaskEvent(EventType.CREATED, AgentRole.USER, f"Task created: {title}"))
        return self._advance_to_step(task, self._pipeline(intent)[0])

    def advance_task(
        self,
        task: Task,
        *,
        actor: AgentRole,
        message: str,
        within_known_rules: bool = True,
        artifacts: Iterable[ArtifactRef] = (),
        ask_user: bool = False,
    ) -> Task:
        task.add_event(TaskEvent(EventType.NOTE, actor, message))
        for artifact in artifacts:
            task.add_artifact(artifact)
            task.add_event(
                TaskEvent(
                    EventType.ARTIFACT_ATTACHED,
                    actor,
                    artifact.summary or artifact.path,
                    metadata=asdict(artifact),
                )
            )

        if ask_user:
            if next_step := self._next_pipeline_step(task):
                task.context["_resume_to"] = next_step.status.value
            task.status = TaskStatus.WAITING_USER
            task.current_assignee = AgentRole.USER
            task.touch()
            task.add_event(TaskEvent(EventType.QUESTION, actor, message))
            return task

        if task.status == TaskStatus.CLOSED:
            return task

        next_step = self._next_pipeline_step(task)
        if next_step is None:
            task.status = TaskStatus.CLOSED
            task.current_assignee = AgentRole.XIAOC
            task.touch()
            task.add_event(TaskEvent(EventType.CLOSED, AgentRole.XIAOC, "Task closed"))
            return task

        if next_step.status == TaskStatus.RECORDED and not self.policy.can_auto_advance(
            within_known_rules=within_known_rules,
            intent=task.intent,
        ):
            task.context["_resume_to"] = next_step.status.value
            task.status = TaskStatus.WAITING_USER
            task.current_assignee = AgentRole.USER
            task.touch()
            task.add_event(
                TaskEvent(
                    EventType.QUESTION,
                    AgentRole.XIAOC,
                    "User review required before recording or closing this task.",
                )
            )
            return task

        return self._advance_to_step(task, next_step)

    def resume_from_user(self, task: Task, message: str) -> Task:
        task.add_event(TaskEvent(EventType.NOTE, AgentRole.USER, message))
        next_step = self._next_pipeline_step(task, from_waiting=True)
        if next_step is None:
            return task
        return self._advance_to_step(task, next_step)

    def _advance_to_step(self, task: Task, step: PipelineStep) -> Task:
        task.status = step.status
        task.current_assignee = step.assignee
        task.touch()
        task.add_event(
            TaskEvent(
                EventType.STATUS_CHANGED,
                AgentRole.SYSTEM,
                f"{step.status.value}: {step.label}",
            )
        )
        return task

    def _pipeline(self, intent: TaskIntent) -> tuple[PipelineStep, ...]:
        return PIPELINES[intent]

    def _next_pipeline_step(self, task: Task, *, from_waiting: bool = False) -> PipelineStep | None:
        pipeline = self._pipeline(task.intent)
        statuses = [step.status for step in pipeline]

        if from_waiting:
            resume_to = task.context.pop("_resume_to", None)
            if resume_to is None:
                return None
            for step in pipeline:
                if step.status.value == resume_to:
                    return step
            return None

        try:
            current_index = statuses.index(task.status)
        except ValueError:
            return pipeline[0]
        if current_index + 1 >= len(pipeline):
            return None
        return pipeline[current_index + 1]
