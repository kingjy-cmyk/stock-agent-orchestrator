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
class BetaLiveRunbook:
    ready_to_start: bool
    stage: str
    readiness_score: int
    readiness_band: str
    callback_url: str
    webhook_url: str
    healthz_url: str
    commands: list[str]
    manual_steps: list[str]
    stop_conditions: list[str]
    evidence_to_collect: list[str]
    next_steps: list[str]
    preflight: dict[str, Any]


def build_beta_live_runbook(
    *,
    config: OrchestratorConfig,
    callback_url: str,
    repo_root: Path,
    config_path: str = "configs/beta.live.toml",
    db_path: str = ".runtime/webhook.db",
    healthz_json_path: str = ".runtime/healthz.json",
    report_path: str = "docs/BETA_VALIDATION_REPORT_ZH.md",
) -> BetaLiveRunbook:
    readiness = run_application_readiness(repo_root)
    preflight = run_beta_live_preflight(config, callback_url=callback_url)
    ready_to_start = preflight.ok
    stage = "ready_for_beta_group_run" if ready_to_start else "fix_preflight_before_beta_group_run"

    return BetaLiveRunbook(
        ready_to_start=ready_to_start,
        stage=stage,
        readiness_score=readiness.score,
        readiness_band=readiness.band,
        callback_url=preflight.callback_url,
        webhook_url=preflight.webhook_url,
        healthz_url=preflight.healthz_url,
        commands=_commands(
            ready_to_start=ready_to_start,
            config_path=config_path,
            callback_url=preflight.callback_url or callback_url,
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
        ),
        manual_steps=_manual_steps(ready_to_start=ready_to_start),
        stop_conditions=_stop_conditions(ready_to_start=ready_to_start),
        evidence_to_collect=_evidence_to_collect(report_path=report_path),
        next_steps=_next_steps(ready_to_start=ready_to_start),
        preflight=preflight_report_to_dict(preflight),
    )


def beta_live_runbook_to_dict(runbook: BetaLiveRunbook) -> dict[str, Any]:
    return asdict(runbook)


def beta_live_runbook_to_markdown(runbook: BetaLiveRunbook) -> str:
    lines = [
        "# 飞书 Beta Live Runbook",
        "",
        f"- ready_to_start: `{str(runbook.ready_to_start).lower()}`",
        f"- stage: `{runbook.stage}`",
        f"- readiness: `{runbook.readiness_score}/100` `{runbook.readiness_band}`",
        f"- callback_url: `{runbook.callback_url or '<missing>'}`",
        f"- webhook_url: `{runbook.webhook_url or '<missing>'}`",
        f"- healthz_url: `{runbook.healthz_url or '<missing>'}`",
        "",
        "## Commands",
    ]
    for command in runbook.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Manual Steps"])
    lines.extend(f"- {item}" for item in runbook.manual_steps)
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in runbook.stop_conditions)
    lines.extend(["", "## Evidence To Collect"])
    lines.extend(f"- {item}" for item in runbook.evidence_to_collect)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in runbook.next_steps)
    return "\n".join(lines)


def _commands(
    *,
    ready_to_start: bool,
    config_path: str,
    callback_url: str,
    db_path: str,
    healthz_json_path: str,
    report_path: str,
) -> list[str]:
    if not ready_to_start:
        return [
            f"stock-agent-orchestrator beta-live-preflight --config {config_path} --callback-url {callback_url} --format markdown",
            f"stock-agent-orchestrator beta-validation-guide --config {config_path} --callback-url {callback_url} --format markdown",
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
        "stock-agent-orchestrator application-readiness --format markdown",
    ]


def _manual_steps(*, ready_to_start: bool) -> list[str]:
    if not ready_to_start:
        return [
            "先替换 configs/beta.live.toml 中的真实飞书 app、群、open_id、verification_token、encrypt_key。",
            "准备公网 HTTPS callback，并确保最终 URL 不使用 localhost 或 http。",
            "重新运行 runbook，直到 ready_to_start 为 true。",
        ]
    return [
        "保持 run-webhook 进程运行，不要同时启动多个写入同一 beta 群的实例。",
        "在飞书开放平台事件订阅中填写 runbook 输出的 webhook_url。",
        "在 beta 群发送：@小C-beta 今天先给我一份候选池。",
        "确认群里出现 BETA 任务卡，并记录任务 ID。",
        "让小智-beta 或小巴-beta 发送带任务 ID 的后续消息，确认同一张任务卡被原地更新。",
    ]


def _stop_conditions(*, ready_to_start: bool) -> list[str]:
    if not ready_to_start:
        return ["preflight 未通过时不要启动 --allow-live-send，也不要配置真实飞书事件订阅。"]
    return [
        "beta-callback-probe 失败时停止，不要继续发群消息。",
        "群里没有出现任务卡时停止，先查 webhook、allowlist 和飞书发送错误。",
        "生成报告时 task_card_message_id 缺失，说明任务卡证据未落库，不能作为申请材料。",
        "/healthz 中 operation_error_count 大于 0 时停止，先定位 last_error。",
        "任何实盘交易相关配置被打开时立即停止；beta 阶段必须 allow_real_trading=false。",
    ]


def _evidence_to_collect(*, report_path: str) -> list[str]:
    return [
        "beta 群委托截图或录屏。",
        "任务卡首次出现截图或录屏。",
        "同一任务后续更新后的任务卡截图或录屏。",
        "collect-beta-evidence 生成的 .runtime/healthz.json。",
        f"`{report_path}`，且报告总体通过为 true。",
    ]


def _next_steps(*, ready_to_start: bool) -> list[str]:
    if ready_to_start:
        return [
            "按 Commands 顺序执行真实 beta 验证。",
            "把生成的验证报告和截图路径提交到仓库。",
            "重新运行 application-readiness，确认进入 ready_with_evidence。",
        ]
    return [
        "修复 preflight 失败项。",
        "不要把当前结果作为真实 beta 或申请证据。",
        "修复后重新生成 runbook。",
    ]
