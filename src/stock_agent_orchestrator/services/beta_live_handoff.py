from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from stock_agent_orchestrator.services.beta_live_intake_checklist import (
    beta_live_intake_checklist_to_dict,
    build_beta_live_intake_checklist,
)


@dataclass(frozen=True, slots=True)
class BetaLiveHandoff:
    ok: bool
    stage: str
    callback_url: str
    shell: str
    task_id: str
    approval_points: list[str]
    required_values: list[dict[str, Any]]
    safe_to_share: list[str]
    secrets: list[str]
    commands: list[str]
    operator_steps: list[str]
    stop_conditions: list[str]
    next_steps: list[str]
    intake_checklist: dict[str, Any]


def build_beta_live_handoff(
    *,
    callback_url: str = "https://your-public-domain.example",
    shell: str = "powershell",
    task_id: str = "BETA-0001",
) -> BetaLiveHandoff:
    normalized_shell = shell.strip().lower()
    checklist = build_beta_live_intake_checklist(shell=normalized_shell)
    normalized_task_id = task_id.strip().upper() or "BETA-0001"
    required_values = [asdict(item) for item in checklist.items]
    secrets = [item["env_name"] for item in required_values if item["sensitive"]]
    safe_to_share = [item["env_name"] for item in required_values if not item["sensitive"]]
    return BetaLiveHandoff(
        ok=True,
        stage="ready_to_collect_real_beta_inputs",
        callback_url=callback_url,
        shell=normalized_shell,
        task_id=normalized_task_id,
        approval_points=_approval_points(),
        required_values=required_values,
        safe_to_share=safe_to_share,
        secrets=secrets,
        commands=_commands(callback_url=callback_url, shell=normalized_shell, task_id=normalized_task_id),
        operator_steps=_operator_steps(),
        stop_conditions=_stop_conditions(),
        next_steps=_next_steps(),
        intake_checklist=beta_live_intake_checklist_to_dict(checklist),
    )


def beta_live_handoff_to_dict(handoff: BetaLiveHandoff) -> dict[str, Any]:
    return asdict(handoff)


def beta_live_handoff_to_markdown(handoff: BetaLiveHandoff) -> str:
    lines = [
        "# 飞书 Beta Live Handoff",
        "",
        f"- ok: `{str(handoff.ok).lower()}`",
        f"- stage: `{handoff.stage}`",
        f"- callback_url: `{handoff.callback_url}`",
        f"- shell: `{handoff.shell}`",
        f"- task_id: `{handoff.task_id}`",
        "",
        "## Approval Points",
    ]
    lines.extend(f"- {item}" for item in handoff.approval_points)
    lines.extend(
        [
            "",
            "## Required Values",
            "",
            "| env | source | sensitive | validation | risk |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in handoff.required_values:
        lines.append(
            f"| `{item['env_name']}` | {item['source']} | `{str(item['sensitive']).lower()}` | {item['validation']} | {item['risk']} |"
        )
    lines.extend(["", "## Safe To Share"])
    lines.extend(f"- `{item}`" for item in handoff.safe_to_share)
    lines.extend(["", "## Secrets"])
    lines.extend(f"- `{item}`" for item in handoff.secrets)
    lines.extend(["", "## Commands"])
    for command in handoff.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Operator Steps"])
    lines.extend(f"- {item}" for item in handoff.operator_steps)
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in handoff.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in handoff.next_steps)
    return "\n".join(lines)


def _approval_points() -> list[str]:
    return [
        "确认使用临时 beta 群，不使用当前正式工作流群。",
        "确认 beta 群成员只包含 BOOS、小C-beta、小智-beta、小巴-beta 和必要测试人员。",
        "确认 beta app 与正式 app 分离，secret 不在聊天或仓库中公开。",
        "确认 callback URL 是公网 HTTPS，且只指向 beta webhook。",
        "确认 final gate 通过前不启动 --allow-live-send。",
    ]


def _commands(*, callback_url: str, shell: str, task_id: str) -> list[str]:
    return [
        f"stock-agent-orchestrator beta-live-handoff --shell {shell} --callback-url {callback_url} --task-id {task_id} --format markdown",
        f"stock-agent-orchestrator beta-live-intake-checklist --shell {shell} --format markdown",
        f"stock-agent-orchestrator beta-live-env-template --shell {shell}",
        "stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown",
        "stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url "
        f"{callback_url} --shell {shell} --format markdown",
        "stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url "
        f"{callback_url} --format markdown",
        f"stock-agent-orchestrator beta-live-final-gate --config configs/beta.live.toml --callback-url {callback_url} --task-id {task_id} --format markdown",
    ]


def _operator_steps() -> list[str]:
    return [
        "先由用户确认 approval points，未确认前不进入真实 beta。",
        "按 Required Values 收集字段；非敏感字段可以截图或文字说明，敏感字段只进环境变量。",
        "用 beta-live-env-template 生成本机填写模板。",
        "用 beta-live-config-from-env 写入 ignored 的 configs/beta.live.toml。",
        "依次运行 config review、readiness bundle、final gate。",
    ]


def _stop_conditions() -> list[str]:
    return [
        "beta 群、beta app、callback URL 任一项不确定时停止。",
        "任何 secret 出现在聊天、GitHub、README、日志截图中时停止并轮换。",
        "configs/beta.live.toml 未被 gitignore 忽略时停止。",
        "final gate 输出 ok=false 时停止。",
        "发现目标群是当前正式工作流群时停止。",
    ]


def _next_steps() -> list[str]:
    return [
        "用户准备 beta 群和飞书开放平台字段。",
        "填写环境变量并生成 ignored 配置。",
        "跑 final gate；通过后再启动 webhook 和 callback probe。",
        "只在临时 beta 群按 message script 发送首轮消息。",
    ]
