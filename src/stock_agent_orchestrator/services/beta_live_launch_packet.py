from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.services.application_readiness import run_application_readiness
from stock_agent_orchestrator.services.beta_live_preflight import (
    preflight_report_to_dict,
    run_beta_live_preflight,
)


@dataclass(frozen=True, slots=True)
class BetaLiveLaunchPacket:
    ready_to_launch: bool
    stage: str
    readiness_score: int
    readiness_band: str
    preflight_ok: bool
    beta_group_isolated: bool
    callback_url: str
    webhook_url: str
    healthz_url: str
    feishu_console_values: dict[str, Any]
    agent_roster: list[dict[str, str]]
    test_messages: list[str]
    approval_gates: list[str]
    evidence_to_capture: list[str]
    commands: list[str]
    stop_conditions: list[str]
    next_steps: list[str]
    preflight: dict[str, Any]


def build_beta_live_launch_packet(
    *,
    config: OrchestratorConfig,
    callback_url: str,
    repo_root: Path,
    config_path: str = "configs/beta.live.toml",
    db_path: str = ".runtime/webhook.db",
    healthz_json_path: str = ".runtime/healthz.json",
    report_path: str = "docs/BETA_VALIDATION_REPORT_ZH.md",
) -> BetaLiveLaunchPacket:
    readiness = run_application_readiness(repo_root)
    preflight = run_beta_live_preflight(config, callback_url=callback_url)
    beta_group_isolated = _beta_group_isolated(config)
    ready_to_launch = preflight.ok and beta_group_isolated
    stage = _stage(preflight_ok=preflight.ok, beta_group_isolated=beta_group_isolated)

    return BetaLiveLaunchPacket(
        ready_to_launch=ready_to_launch,
        stage=stage,
        readiness_score=readiness.score,
        readiness_band=readiness.band,
        preflight_ok=preflight.ok,
        beta_group_isolated=beta_group_isolated,
        callback_url=preflight.callback_url,
        webhook_url=preflight.webhook_url,
        healthz_url=preflight.healthz_url,
        feishu_console_values=_feishu_console_values(config=config, webhook_url=preflight.webhook_url),
        agent_roster=_agent_roster(config),
        test_messages=_test_messages(config),
        approval_gates=_approval_gates(),
        evidence_to_capture=_evidence_to_capture(report_path=report_path),
        commands=_commands(
            ready_to_launch=ready_to_launch,
            config_path=config_path,
            callback_url=preflight.callback_url or callback_url,
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
        ),
        stop_conditions=_stop_conditions(ready_to_launch=ready_to_launch),
        next_steps=_next_steps(ready_to_launch=ready_to_launch),
        preflight=preflight_report_to_dict(preflight),
    )


def beta_live_launch_packet_to_dict(packet: BetaLiveLaunchPacket) -> dict[str, Any]:
    return asdict(packet)


def beta_live_launch_packet_to_markdown(packet: BetaLiveLaunchPacket) -> str:
    lines = [
        "# 飞书 Beta Live Launch Packet",
        "",
        f"- ready_to_launch: `{str(packet.ready_to_launch).lower()}`",
        f"- stage: `{packet.stage}`",
        f"- readiness: `{packet.readiness_score}/100` `{packet.readiness_band}`",
        f"- preflight_ok: `{str(packet.preflight_ok).lower()}`",
        f"- beta_group_isolated: `{str(packet.beta_group_isolated).lower()}`",
        f"- webhook_url: `{packet.webhook_url or '<missing>'}`",
        f"- healthz_url: `{packet.healthz_url or '<missing>'}`",
        "",
        "## Feishu Console Values",
    ]
    for key, value in packet.feishu_console_values.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Agent Roster"])
    for agent in packet.agent_roster:
        lines.append(f"- {agent['role']}: {agent['name']} (`{agent['open_id']}`)")
    lines.extend(["", "## Test Messages"])
    lines.extend(f"- {item}" for item in packet.test_messages)
    lines.extend(["", "## Approval Gates"])
    lines.extend(f"- {item}" for item in packet.approval_gates)
    lines.extend(["", "## Evidence To Capture"])
    lines.extend(f"- {item}" for item in packet.evidence_to_capture)
    lines.extend(["", "## Commands"])
    for command in packet.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in packet.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in packet.next_steps)
    return "\n".join(lines)


def _beta_group_isolated(config: OrchestratorConfig) -> bool:
    allowlist = {item.strip() for item in config.feishu.send_allowlist}
    return (
        config.project.environment == "beta"
        and config.project.mode == "active"
        and config.feishu.group_chat_id.strip() in allowlist
        and config.feishu.send_mode == "live"
        and not config.automation.allow_real_trading
    )


def _stage(*, preflight_ok: bool, beta_group_isolated: bool) -> str:
    if not preflight_ok:
        return "fix_preflight_before_launch_packet"
    if not beta_group_isolated:
        return "fix_beta_group_isolation_before_launch"
    return "ready_to_execute_beta_launch"


def _feishu_console_values(*, config: OrchestratorConfig, webhook_url: str) -> dict[str, Any]:
    return {
        "app_id": config.feishu.app_id or "<missing>",
        "callback_url": webhook_url or "<missing>",
        "event_subscription": "im.message.receive_v1",
        "target_group_chat_id": config.feishu.group_chat_id or "<missing>",
        "send_allowlist_contains_group": str(config.feishu.group_chat_id in config.feishu.send_allowlist).lower(),
        "verification_token_configured": str(bool(config.feishu.verification_token.strip())).lower(),
        "encrypt_key_configured": str(bool(config.feishu.encrypt_key.strip())).lower(),
        "secrets_rendered": "false",
    }


def _agent_roster(config: OrchestratorConfig) -> list[dict[str, str]]:
    return [
        {"role": "owner", "name": config.roles.owner, "open_id": config.feishu.owner_open_id},
        {"role": "data", "name": config.roles.data, "open_id": config.feishu.data_open_id},
        {"role": "analyst", "name": config.roles.analyst, "open_id": config.feishu.analyst_open_id},
    ]


def _test_messages(config: OrchestratorConfig) -> list[str]:
    return [
        f"BOOS -> @{config.roles.owner} 今天先给我一份候选池",
        f"{config.roles.data} -> BETA-0001 七层数据已拉取，等待小巴判断",
        f"{config.roles.analyst} -> BETA-0001 已完成 RSI 候选池初判，建议进入复盘记录",
    ]


def _approval_gates() -> list[str]:
    return [
        "首条 BOOS 委托必须生成 BETA-* 任务。",
        "任务卡必须发到 beta 群，不允许发到正式群。",
        "小智-beta / 小巴-beta 的后续消息必须更新同一张任务卡。",
        "新规则或越界事项必须进入用户审阅，不允许自动执行。",
        "beta 阶段必须保持 allow_real_trading=false。",
    ]


def _evidence_to_capture(*, report_path: str) -> list[str]:
    return [
        "飞书开放平台事件订阅 callback 配置截图。",
        "beta 群 BOOS 首条委托截图或录屏。",
        "BETA-* 任务卡首次出现截图或录屏。",
        "同一任务卡被小智-beta / 小巴-beta 后续消息原地更新的截图或录屏。",
        ".runtime/healthz.json，需显示 connected 且 operation_error_count 为 0。",
        f"{report_path}，且报告总体通过为 true。",
    ]


def _commands(
    *,
    ready_to_launch: bool,
    config_path: str,
    callback_url: str,
    db_path: str,
    healthz_json_path: str,
    report_path: str,
) -> list[str]:
    if not ready_to_launch:
        return [
            f"stock-agent-orchestrator beta-live-preflight --config {config_path} --callback-url {callback_url} --format markdown",
            f"stock-agent-orchestrator beta-live-launch-packet --config {config_path} --callback-url {callback_url} --format markdown",
        ]
    return [
        f"stock-agent-orchestrator run-webhook --config {config_path} --db {db_path} --allow-live-send",
        f"stock-agent-orchestrator beta-callback-probe --config {config_path} --callback-url {callback_url} --format markdown",
        (
            "stock-agent-orchestrator collect-beta-evidence "
            f"--config {config_path} "
            f"--callback-url {callback_url} "
            "--commit <git-commit> "
            f"--db {db_path} "
            f"--healthz-json {healthz_json_path} "
            f"--report-output {report_path} "
            "--beta-group-name <beta-group-name> "
            "--feishu-app-name <feishu-app-name> "
            "--task-card-screenshot <screenshot-or-gif-path>"
        ),
    ]


def _stop_conditions(*, ready_to_launch: bool) -> list[str]:
    if not ready_to_launch:
        return ["ready_to_launch 为 false 时不要启动 --allow-live-send，也不要把 callback 接到真实飞书应用。"]
    return [
        "callback probe 失败时停止。",
        "收到非 beta 群消息时停止并检查 group_chat_id 和 send_allowlist。",
        "任务卡没有出现或没有 task_card_message_id 时停止。",
        "operation_error_count 大于 0 时停止。",
        "任何实盘交易配置被打开时停止。",
    ]


def _next_steps(*, ready_to_launch: bool) -> list[str]:
    if ready_to_launch:
        return [
            "按 Commands 启动 webhook 和 callback probe。",
            "在飞书开放平台填入 Feishu Console Values。",
            "在 beta 群按 Test Messages 执行首轮验证并截图。",
            "运行 collect-beta-evidence 生成验证报告。",
        ]
    return [
        "修复 preflight 或 beta group isolation 失败项。",
        "重新生成 launch packet。",
        "不要把当前结果作为申请证据。",
    ]
