from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.services.application_readiness import (
    readiness_report_to_dict,
    run_application_readiness,
)
from stock_agent_orchestrator.services.beta_live_config_review import (
    beta_live_config_review_to_dict,
    build_beta_live_config_review,
)
from stock_agent_orchestrator.services.beta_live_final_gate import (
    beta_live_final_gate_to_dict,
    build_beta_live_final_gate,
)
from stock_agent_orchestrator.services.beta_live_handoff import (
    beta_live_handoff_to_dict,
    build_beta_live_handoff,
)
from stock_agent_orchestrator.services.beta_live_readiness_bundle import (
    beta_live_readiness_bundle_to_dict,
    build_beta_live_readiness_bundle,
)


@dataclass(frozen=True, slots=True)
class BetaLiveControlPanel:
    ok: bool
    stage: str
    next_action: str
    readiness_score: int
    readiness_band: str
    event_mode: str
    callback_url: str
    config_path: str
    task_id: str
    report_path: str
    checks: list[dict[str, str]]
    commands: list[str]
    stop_conditions: list[str]
    readiness: dict[str, Any]
    handoff: dict[str, Any]
    config_review: dict[str, Any]
    readiness_bundle: dict[str, Any]
    final_gate: dict[str, Any]


def build_beta_live_control_panel(
    *,
    repo_root: Path = Path("."),
    config_path: Path = Path("configs/beta.live.toml"),
    callback_url: str = "https://your-public-domain.example",
    db_path: str = ".runtime/webhook.db",
    healthz_json_path: str = ".runtime/healthz.json",
    report_path: str = "docs/BETA_VALIDATION_REPORT_ZH.md",
    host: str = "127.0.0.1",
    port: int = 8787,
    shell: str = "powershell",
    task_id: str = "BETA-0001",
) -> BetaLiveControlPanel:
    normalized_task_id = task_id.strip().upper() or "BETA-0001"
    readiness = run_application_readiness(repo_root)
    handoff = build_beta_live_handoff(callback_url=callback_url, shell=shell, task_id=normalized_task_id)
    config_review = build_beta_live_config_review(
        repo_root=repo_root,
        config_path=config_path,
        callback_url=callback_url,
        shell=shell,
    )
    readiness_bundle = build_beta_live_readiness_bundle(
        repo_root=repo_root,
        config_path=config_path,
        callback_url=callback_url,
        db_path=db_path,
        healthz_json_path=healthz_json_path,
        report_path=report_path,
    )
    final_gate = build_beta_live_final_gate(
        repo_root=repo_root,
        config_path=config_path,
        callback_url=callback_url,
        db_path=db_path,
        healthz_json_path=healthz_json_path,
        report_path=report_path,
        host=host,
        port=port,
        task_id=normalized_task_id,
        shell=shell,
    )
    report_exists = (repo_root / report_path).exists()
    stage = _stage(
        report_exists=report_exists,
        config_review_ok=config_review.ok,
        readiness_bundle_ok=readiness_bundle.ok,
        final_gate_ok=final_gate.ok,
    )
    event_mode = final_gate.event_mode
    next_action = _next_action(stage=stage, event_mode=event_mode)
    checks = _checks(
        handoff_ok=handoff.ok,
        config_review_ok=config_review.ok,
        readiness_bundle_ok=readiness_bundle.ok,
        final_gate_ok=final_gate.ok,
        report_exists=report_exists,
    )
    return BetaLiveControlPanel(
        ok=stage in {"ready_to_start_real_beta_execution", "real_beta_evidence_present"},
        stage=stage,
        next_action=next_action,
        readiness_score=readiness.score,
        readiness_band=readiness.band,
        event_mode=event_mode,
        callback_url=callback_url,
        config_path=_path_text(str(config_path)),
        task_id=normalized_task_id,
        report_path=report_path,
        checks=checks,
        commands=_commands(
            stage=stage,
            event_mode=event_mode,
            callback_url=callback_url,
            config_path=_path_text(str(config_path)),
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
            host=host,
            port=port,
            shell=shell,
            task_id=normalized_task_id,
        ),
        stop_conditions=_stop_conditions(),
        readiness=readiness_report_to_dict(readiness),
        handoff=beta_live_handoff_to_dict(handoff),
        config_review=beta_live_config_review_to_dict(config_review),
        readiness_bundle=beta_live_readiness_bundle_to_dict(readiness_bundle),
        final_gate=beta_live_final_gate_to_dict(final_gate),
    )


def beta_live_control_panel_to_dict(panel: BetaLiveControlPanel) -> dict[str, Any]:
    return asdict(panel)


def beta_live_control_panel_to_markdown(panel: BetaLiveControlPanel) -> str:
    lines = [
        "# 飞书 Beta Live Control Panel",
        "",
        f"- ok: `{str(panel.ok).lower()}`",
        f"- stage: `{panel.stage}`",
        f"- next_action: `{panel.next_action}`",
        f"- readiness: `{panel.readiness_score}/100` `{panel.readiness_band}`",
        f"- event_mode: `{panel.event_mode}`",
        f"- config_path: `{panel.config_path}`",
        f"- callback_url: `{panel.callback_url}`",
        f"- task_id: `{panel.task_id}`",
        f"- report_path: `{panel.report_path}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{item['status']}` {item['name']}: {item['message']}" for item in panel.checks)
    lines.extend(["", "## Gate Summary"])
    lines.extend(
        [
            f"- config_review: `{panel.config_review['stage']}`",
            f"- readiness_bundle: `{panel.readiness_bundle['stage']}`",
            f"- final_gate: `{panel.final_gate['stage']}`",
        ]
    )
    lines.extend(["", "## Commands"])
    for command in panel.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in panel.stop_conditions)
    return "\n".join(lines)


def _stage(*, report_exists: bool, config_review_ok: bool, readiness_bundle_ok: bool, final_gate_ok: bool) -> str:
    if report_exists:
        return "real_beta_evidence_present"
    if not config_review_ok:
        return "collect_or_fix_real_beta_config"
    if not readiness_bundle_ok:
        return "fix_beta_readiness_bundle"
    if not final_gate_ok:
        return "fix_beta_final_gate"
    return "ready_to_start_real_beta_execution"


def _next_action(*, stage: str, event_mode: str) -> str:
    ready_action = (
        "start_long_connection_then_send_beta_messages"
        if event_mode == "long_connection"
        else "start_webhook_probe_callback_then_send_beta_messages"
    )
    mapping = {
        "real_beta_evidence_present": "rerun_application_readiness_and_prepare_application",
        "collect_or_fix_real_beta_config": "fill_or_review_configs_beta_live_toml",
        "fix_beta_readiness_bundle": "run_readiness_bundle_and_fix_failed_gate",
        "fix_beta_final_gate": "run_final_gate_and_fix_failed_gate",
        "ready_to_start_real_beta_execution": ready_action,
    }
    return mapping[stage]


def _checks(
    *,
    handoff_ok: bool,
    config_review_ok: bool,
    readiness_bundle_ok: bool,
    final_gate_ok: bool,
    report_exists: bool,
) -> list[dict[str, str]]:
    return [
        _check("handoff", handoff_ok, "handoff is available", "handoff failed"),
        _check("config_review", config_review_ok, "real beta config review passes", "real beta config review does not pass"),
        _check("readiness_bundle", readiness_bundle_ok, "readiness bundle allows real beta validation", "readiness bundle does not allow real beta validation"),
        _check("final_gate", final_gate_ok, "final gate allows real beta execution", "final gate blocks real beta execution"),
        _check("real_beta_evidence", report_exists, "real beta validation report exists", "real beta validation report is missing"),
    ]


def _check(name: str, ok: bool, pass_message: str, fail_message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "message": pass_message if ok else fail_message}


def _commands(
    *,
    stage: str,
    event_mode: str,
    callback_url: str,
    config_path: str,
    db_path: str,
    healthz_json_path: str,
    report_path: str,
    host: str,
    port: int,
    shell: str,
    task_id: str,
) -> list[str]:
    if stage == "real_beta_evidence_present":
        return ["stock-agent-orchestrator application-readiness --format markdown"]
    if stage == "collect_or_fix_real_beta_config":
        callback_arg = f" --callback-url {callback_url}" if callback_url else ""
        return [
            f"stock-agent-orchestrator beta-live-handoff --shell {shell}{callback_arg} --task-id {task_id} --format markdown",
            f"stock-agent-orchestrator beta-live-env-template --shell {shell}",
            f"stock-agent-orchestrator beta-live-config-review --config {config_path}{callback_arg} --shell {shell} --format markdown",
        ]
    if stage == "fix_beta_readiness_bundle":
        callback_arg = f" --callback-url {callback_url}" if callback_url else ""
        return [
            f"stock-agent-orchestrator beta-live-readiness-bundle --config {config_path}{callback_arg} --db {db_path} --healthz-json {healthz_json_path} --report-output {report_path} --format markdown",
        ]
    if stage == "fix_beta_final_gate":
        callback_arg = f" --callback-url {callback_url}" if callback_url else ""
        return [
            f"stock-agent-orchestrator beta-live-final-gate --config {config_path}{callback_arg} --db {db_path} --healthz-json {healthz_json_path} --report-output {report_path} --host {host} --port {port} --task-id {task_id} --shell {shell} --format markdown",
        ]
    if event_mode == "long_connection":
        return [
            f"stock-agent-orchestrator run-long-connection --config {config_path} --db {db_path} --allow-live-send",
            f"stock-agent-orchestrator beta-live-message-script --task-id {task_id} --format markdown",
            f"stock-agent-orchestrator collect-beta-evidence --config {config_path} --callback-url long_connection --db {db_path} --task-id {task_id} --healthz-json {healthz_json_path} --report-output {report_path} --commit <commit>",
        ]
    return [
        f"stock-agent-orchestrator run-webhook --config {config_path} --db {db_path} --host {host} --port {port} --allow-live-send",
        f"stock-agent-orchestrator beta-callback-probe --config {config_path} --callback-url {callback_url} --format markdown",
        f"stock-agent-orchestrator beta-live-message-script --task-id {task_id} --format markdown",
        f"stock-agent-orchestrator collect-beta-evidence --config {config_path} --callback-url {callback_url} --db {db_path} --task-id {task_id} --healthz-json {healthz_json_path} --report-output {report_path} --commit <commit>",
    ]


def _stop_conditions() -> list[str]:
    return [
        "control panel 不会联网、不启动 webhook、不启动长链接、不发送飞书消息。",
        "stage 不是 ready_to_start_real_beta_execution 时不要启动 --allow-live-send。",
        "目标群不是临时 beta 群时停止。",
        "任何 secret 出现在公开输出、GitHub 或群聊时停止并轮换。",
        "/healthz 出现 operation_error_count > 0 时停止。",
    ]


def _path_text(path: str) -> str:
    return path.replace("\\", "/")
