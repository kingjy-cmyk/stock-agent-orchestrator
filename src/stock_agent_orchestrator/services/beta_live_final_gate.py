from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.services.beta_callback_deploy_plan import (
    beta_callback_deploy_plan_to_dict,
    build_beta_callback_deploy_plan,
)
from stock_agent_orchestrator.services.beta_live_config_review import (
    beta_live_config_review_to_dict,
    build_beta_live_config_review,
)
from stock_agent_orchestrator.services.beta_live_message_script import (
    beta_live_message_script_to_dict,
    build_beta_live_message_script,
)
from stock_agent_orchestrator.services.beta_live_readiness_bundle import (
    beta_live_readiness_bundle_to_dict,
    build_beta_live_readiness_bundle,
)


@dataclass(frozen=True, slots=True)
class BetaLiveFinalGate:
    ok: bool
    stage: str
    config_path: str
    callback_url: str
    task_id: str
    checks: list[dict[str, str]]
    config_review: dict[str, Any]
    readiness_bundle: dict[str, Any]
    callback_deploy_plan: dict[str, Any]
    message_script: dict[str, Any]
    commands: list[str]
    stop_conditions: list[str]
    next_steps: list[str]


def build_beta_live_final_gate(
    *,
    repo_root: Path = Path("."),
    config_path: Path = Path("configs/beta.live.toml"),
    callback_url: str,
    task_id: str = "BETA-0001",
    db_path: str = ".runtime/webhook.db",
    healthz_json_path: str = ".runtime/healthz.json",
    report_path: str = "docs/BETA_VALIDATION_REPORT_ZH.md",
    host: str = "127.0.0.1",
    port: int = 8787,
    shell: str = "powershell",
) -> BetaLiveFinalGate:
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
    deploy_plan = build_beta_callback_deploy_plan(
        callback_url=callback_url,
        config_path=str(config_path),
        db_path=db_path,
        host=host,
        port=port,
    )
    message_script = build_beta_live_message_script(task_id=task_id)
    checks = _checks(
        config_review_ok=config_review.ok,
        readiness_ok=readiness_bundle.ok,
        deploy_plan_ok=deploy_plan.ok,
        message_script_ok=message_script.ok,
    )
    ok = all(item["status"] == "pass" for item in checks)
    stage = _stage(
        config_review_ok=config_review.ok,
        readiness_ok=readiness_bundle.ok,
        deploy_plan_ok=deploy_plan.ok,
        message_script_ok=message_script.ok,
    )
    normalized_task_id = task_id.strip().upper() or "BETA-0001"
    config_path_text = _path_text(str(config_path))
    return BetaLiveFinalGate(
        ok=ok,
        stage=stage,
        config_path=config_path_text,
        callback_url=callback_url,
        task_id=normalized_task_id,
        checks=checks,
        config_review=beta_live_config_review_to_dict(config_review),
        readiness_bundle=beta_live_readiness_bundle_to_dict(readiness_bundle),
        callback_deploy_plan=beta_callback_deploy_plan_to_dict(deploy_plan),
        message_script=beta_live_message_script_to_dict(message_script),
        commands=_commands(
            ok=ok,
            config_path=config_path_text,
            callback_url=callback_url,
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
            host=host,
            port=port,
            task_id=normalized_task_id,
            shell=shell,
        ),
        stop_conditions=_stop_conditions(),
        next_steps=_next_steps(ok=ok),
    )


def beta_live_final_gate_to_dict(gate: BetaLiveFinalGate) -> dict[str, Any]:
    return asdict(gate)


def beta_live_final_gate_to_markdown(gate: BetaLiveFinalGate) -> str:
    lines = [
        "# 飞书 Beta Live Final Gate",
        "",
        f"- ok: `{str(gate.ok).lower()}`",
        f"- stage: `{gate.stage}`",
        f"- config_path: `{gate.config_path}`",
        f"- callback_url: `{gate.callback_url}`",
        f"- task_id: `{gate.task_id}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{item['status']}` {item['name']}: {item['message']}" for item in gate.checks)
    lines.extend(["", "## Gate Summary"])
    lines.extend(
        [
            f"- config_review: `{gate.config_review['stage']}`",
            f"- readiness_bundle: `{gate.readiness_bundle['stage']}`",
            f"- callback_deploy_plan: `{gate.callback_deploy_plan['stage']}`",
            f"- message_script: `{gate.message_script['stage']}`",
        ]
    )
    lines.extend(["", "## Commands"])
    for command in gate.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in gate.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in gate.next_steps)
    return "\n".join(lines)


def _checks(
    *,
    config_review_ok: bool,
    readiness_ok: bool,
    deploy_plan_ok: bool,
    message_script_ok: bool,
) -> list[dict[str, str]]:
    return [
        _check("config_review", config_review_ok, "real beta config review passes", "real beta config review does not pass"),
        _check("readiness_bundle", readiness_ok, "readiness bundle allows real beta validation", "readiness bundle does not allow real beta validation"),
        _check("callback_deploy_plan", deploy_plan_ok, "callback deployment plan passes", "callback deployment plan does not pass"),
        _check("message_script", message_script_ok, "message script is ready", "message script is not ready"),
    ]


def _stage(
    *,
    config_review_ok: bool,
    readiness_ok: bool,
    deploy_plan_ok: bool,
    message_script_ok: bool,
) -> str:
    if not config_review_ok:
        return "fix_beta_live_config_review"
    if not readiness_ok:
        return "fix_beta_live_readiness_bundle"
    if not deploy_plan_ok:
        return "fix_beta_callback_deploy_plan"
    if not message_script_ok:
        return "fix_beta_live_message_script"
    return "ready_to_execute_real_beta_validation"


def _path_text(path: str) -> str:
    return path.replace("\\", "/")


def _check(name: str, ok: bool, pass_message: str, fail_message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "message": pass_message if ok else fail_message}


def _commands(
    *,
    ok: bool,
    config_path: str,
    callback_url: str,
    db_path: str,
    healthz_json_path: str,
    report_path: str,
    host: str,
    port: int,
    task_id: str,
    shell: str,
) -> list[str]:
    if not ok:
        return [
            f"stock-agent-orchestrator beta-live-config-review --config {config_path} --callback-url {callback_url} --shell {shell} --format markdown",
            f"stock-agent-orchestrator beta-live-readiness-bundle --config {config_path} --callback-url {callback_url} --db {db_path} --healthz-json {healthz_json_path} --report-output {report_path} --format markdown",
            f"stock-agent-orchestrator beta-callback-deploy-plan --callback-url {callback_url} --config {config_path} --db {db_path} --host {host} --port {port} --format markdown",
        ]
    return [
        f"stock-agent-orchestrator run-webhook --config {config_path} --db {db_path} --host {host} --port {port} --allow-live-send",
        f"stock-agent-orchestrator beta-callback-probe --config {config_path} --callback-url {callback_url} --format markdown",
        f"stock-agent-orchestrator beta-live-message-script --task-id {task_id} --format markdown",
        f"stock-agent-orchestrator collect-beta-evidence --config {config_path} --callback-url {callback_url} --db {db_path} --task-id {task_id} --healthz-json {healthz_json_path} --report-output {report_path} --commit <commit>",
    ]


def _stop_conditions() -> list[str]:
    return [
        "Final gate ok=false 时不要启动 --allow-live-send。",
        "任一子 gate 失败时不要配置飞书事件订阅或发送 beta 群消息。",
        "readiness bundle 未进入 ready_for_real_beta_group_validation 时停止。",
        "callback_url 不是公网 https 时停止。",
        "真实配置未通过 config review 时停止。",
        "任何消息会进入当前正式群时停止。",
        "/healthz 出现 operation_error_count > 0 时停止。",
        "beta 群消息没有按 message script 执行时不要收集成功证据。",
    ]


def _next_steps(*, ok: bool) -> list[str]:
    if ok:
        return [
            "Start run-webhook with the generated command.",
            "Run beta-callback-probe.",
            "Configure Feishu event subscription to the public /webhook URL.",
            "Send beta group messages according to beta-live-message-script.",
            "Run collect-beta-evidence and commit docs/BETA_VALIDATION_REPORT_ZH.md.",
        ]
    return [
        "Fix failed final gate checks.",
        "Re-run beta-live-final-gate before touching the real beta group.",
    ]
