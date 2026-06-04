from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BetaLiveMessageStep:
    step: int
    sender: str
    message: str
    expected_task_id: str
    expected_status: str
    expected_card_action: str
    evidence: str
    failure_signal: str


@dataclass(frozen=True, slots=True)
class BetaLiveMessageScript:
    ok: bool
    stage: str
    delegate_message: str
    steps: list[BetaLiveMessageStep]
    acceptance_criteria: list[str]
    commands_before: list[str]
    commands_after: list[str]
    stop_conditions: list[str]
    next_steps: list[str]


def build_beta_live_message_script(*, task_id: str = "BETA-0001") -> BetaLiveMessageScript:
    normalized_task_id = task_id.strip().upper() or "BETA-0001"
    delegate_message = "@小C-beta 今天先给我一份候选池"
    return BetaLiveMessageScript(
        ok=True,
        stage="ready_to_execute_beta_group_message_script",
        delegate_message=delegate_message,
        steps=_steps(task_id=normalized_task_id, delegate_message=delegate_message),
        acceptance_criteria=_acceptance_criteria(task_id=normalized_task_id),
        commands_before=_commands_before(),
        commands_after=_commands_after(task_id=normalized_task_id),
        stop_conditions=_stop_conditions(),
        next_steps=_next_steps(),
    )


def beta_live_message_script_to_dict(script: BetaLiveMessageScript) -> dict[str, Any]:
    return asdict(script)


def beta_live_message_script_to_markdown(script: BetaLiveMessageScript) -> str:
    lines = [
        "# 飞书 Beta Live Message Script",
        "",
        f"- ok: `{str(script.ok).lower()}`",
        f"- stage: `{script.stage}`",
        f"- delegate_message: `{script.delegate_message}`",
        "",
        "## Commands Before",
    ]
    for command in script.commands_before:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Message Steps"])
    for item in script.steps:
        lines.extend(
            [
                "",
                f"### Step {item.step}: {item.sender}",
                "",
                "```text",
                item.message,
                "```",
                f"- expected_task_id: `{item.expected_task_id}`",
                f"- expected_status: `{item.expected_status}`",
                f"- expected_card_action: `{item.expected_card_action}`",
                f"- evidence: {item.evidence}",
                f"- failure_signal: {item.failure_signal}",
            ]
        )
    lines.extend(["", "## Acceptance Criteria"])
    lines.extend(f"- {item}" for item in script.acceptance_criteria)
    lines.extend(["", "## Commands After"])
    for command in script.commands_after:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in script.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in script.next_steps)
    return "\n".join(lines)


def _steps(*, task_id: str, delegate_message: str) -> list[BetaLiveMessageStep]:
    return [
        BetaLiveMessageStep(
            step=1,
            sender="BOOS",
            message=delegate_message,
            expected_task_id=task_id,
            expected_status="planned",
            expected_card_action="send new task card",
            evidence="截图或录屏：beta 群出现首张任务卡，任务 ID 与预期一致。",
            failure_signal="没有任务卡、任务 ID 不以 BETA- 开头、或任务卡发到正式群。",
        ),
        BetaLiveMessageStep(
            step=2,
            sender="小智-beta",
            message=f"{task_id} 七层数据已拉取，等待小巴判断",
            expected_task_id=task_id,
            expected_status="scanning",
            expected_card_action="update existing task card",
            evidence="截图或录屏：同一张任务卡原地更新，未新增第二张卡。",
            failure_signal="新建了第二个任务、任务卡 message_id 未复用、或消息没有绑定到目标任务。",
        ),
        BetaLiveMessageStep(
            step=3,
            sender="小巴-beta",
            message=f"{task_id} RSI 候选池初判完成，建议进入复盘记录",
            expected_task_id=task_id,
            expected_status="enriching",
            expected_card_action="update existing task card again",
            evidence="截图或录屏：同一任务卡再次更新，任务 context 中 task_card_update_count 增加。",
            failure_signal="任务卡未更新、operation_error_count 增加、或 agent 身份识别错误。",
        ),
    ]


def _acceptance_criteria(*, task_id: str) -> list[str]:
    return [
        f"SQLite 中存在 `{task_id}`。",
        "任务 context 存在 `task_card_message_id`。",
        "任务 context 中 `task_card_send_count=1`。",
        "任务 context 中 `task_card_update_count>=2`。",
        "healthz 中 gateway status 为 `connected`。",
        "healthz 中 operation_error_count 为 0。",
        "beta 群截图或录屏覆盖首发任务卡和至少一次原地更新。",
    ]


def _commands_before() -> list[str]:
    return [
        "stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown",
        "stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --format markdown",
        "stock-agent-orchestrator beta-callback-probe --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown",
    ]


def _commands_after(*, task_id: str) -> list[str]:
    return [
        f"stock-agent-orchestrator beta-validation-report --config configs/beta.live.toml --callback-url https://your-public-domain.example --db .runtime/webhook.db --task-id {task_id} --healthz-json .runtime/healthz.json --format markdown",
        f"stock-agent-orchestrator collect-beta-evidence --config configs/beta.live.toml --callback-url https://your-public-domain.example --db .runtime/webhook.db --task-id {task_id} --healthz-json .runtime/healthz.json --report-output docs/BETA_VALIDATION_REPORT_ZH.md --commit <commit>",
        "stock-agent-orchestrator application-readiness --format markdown",
    ]


def _stop_conditions() -> list[str]:
    return [
        "任一前置命令失败时不要在 beta 群发消息。",
        "首条 BOOS 委托没有生成任务卡时停止。",
        "小智-beta 或小巴-beta 后续消息新建了任务而不是更新原任务时停止。",
        "任务卡更新失败或 healthz 出现 operation_error_count > 0 时停止。",
        "任何消息发到正式群时停止并检查 group_chat_id / send_allowlist。",
    ]


def _next_steps() -> list[str]:
    return [
        "按 Commands Before 完成前置检查。",
        "在临时 beta 群按 Message Steps 逐条发送并截图。",
        "按 Commands After 生成真实 beta 验证报告。",
    ]
