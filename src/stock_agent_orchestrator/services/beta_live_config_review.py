from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.services.beta_live_config_status import (
    BetaLiveConfigStatus,
    beta_live_config_status_to_dict,
    inspect_beta_live_config,
)
from stock_agent_orchestrator.services.beta_live_intake_checklist import (
    beta_live_intake_checklist_to_dict,
    build_beta_live_intake_checklist,
)


@dataclass(frozen=True, slots=True)
class BetaLiveConfigReview:
    ok: bool
    stage: str
    config_path: str
    callback_url: str
    gitignored: bool
    ready_for_preflight: bool
    sensitive_fields_redacted: bool
    checks: list[dict[str, str]]
    config_status: dict[str, Any]
    intake_checklist: dict[str, Any]
    commands: list[str]
    stop_conditions: list[str]
    next_steps: list[str]


def build_beta_live_config_review(
    *,
    config_path: Path = Path("configs/beta.live.toml"),
    repo_root: Path = Path("."),
    callback_url: str = "https://your-public-domain.example",
    shell: str = "powershell",
) -> BetaLiveConfigReview:
    status = inspect_beta_live_config(config_path=config_path, repo_root=repo_root)
    checklist = build_beta_live_intake_checklist(shell=shell)
    sensitive_fields_redacted = _sensitive_fields_redacted(status)
    ok = bool(status.ready_for_preflight and sensitive_fields_redacted)
    stage = _stage(status=status, sensitive_fields_redacted=sensitive_fields_redacted)
    return BetaLiveConfigReview(
        ok=ok,
        stage=stage,
        config_path=str(config_path),
        callback_url=callback_url,
        gitignored=status.gitignored,
        ready_for_preflight=status.ready_for_preflight,
        sensitive_fields_redacted=sensitive_fields_redacted,
        checks=_checks(status=status, sensitive_fields_redacted=sensitive_fields_redacted),
        config_status=beta_live_config_status_to_dict(status),
        intake_checklist=beta_live_intake_checklist_to_dict(checklist),
        commands=_commands(config_path=str(config_path), callback_url=callback_url, shell=shell, ok=ok),
        stop_conditions=_stop_conditions(),
        next_steps=_next_steps(ok=ok),
    )


def beta_live_config_review_to_dict(review: BetaLiveConfigReview) -> dict[str, Any]:
    return asdict(review)


def beta_live_config_review_to_markdown(review: BetaLiveConfigReview) -> str:
    lines = [
        "# 飞书 Beta Live Config Review",
        "",
        f"- ok: `{str(review.ok).lower()}`",
        f"- stage: `{review.stage}`",
        f"- config_path: `{review.config_path}`",
        f"- callback_url: `{review.callback_url}`",
        f"- gitignored: `{str(review.gitignored).lower()}`",
        f"- ready_for_preflight: `{str(review.ready_for_preflight).lower()}`",
        f"- sensitive_fields_redacted: `{str(review.sensitive_fields_redacted).lower()}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{item['status']}` {item['name']}: {item['message']}" for item in review.checks)
    lines.extend(["", "## Field Status"])
    for item in review.config_status["field_statuses"]:
        lines.append(f"- `{item['status']}` {item['field']}: {item['value']}")
    lines.extend(["", "## Commands"])
    for command in review.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in review.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in review.next_steps)
    return "\n".join(lines)


def _sensitive_fields_redacted(status: BetaLiveConfigStatus) -> bool:
    sensitive = [item for item in status.field_statuses if item.sensitive]
    safe_values = {"<redacted>", "<config file missing>", "<replace-me>", "<config parse failed>", "<missing>"}
    return bool(sensitive) and all(item.value in safe_values for item in sensitive)


def _stage(*, status: BetaLiveConfigStatus, sensitive_fields_redacted: bool) -> str:
    if not status.exists:
        return "create_real_beta_config"
    if not status.gitignored:
        return "protect_real_beta_config_before_review"
    if not sensitive_fields_redacted:
        return "fix_secret_redaction_before_review"
    if not status.ready_for_preflight:
        return "complete_real_beta_config"
    return "ready_for_beta_live_readiness_bundle"


def _checks(*, status: BetaLiveConfigStatus, sensitive_fields_redacted: bool) -> list[dict[str, str]]:
    return [
        _check("config_exists", status.exists, "config file exists", "config file is missing"),
        _check("config_gitignored", status.gitignored, "config path is gitignored", "config path is not gitignored"),
        _check(
            "sensitive_fields_redacted",
            sensitive_fields_redacted,
            "sensitive fields are redacted in review output",
            "sensitive field redaction failed",
        ),
        _check(
            "ready_for_preflight",
            status.ready_for_preflight,
            "config is ready for preflight",
            "config is not ready for preflight",
        ),
    ]


def _check(name: str, ok: bool, pass_message: str, fail_message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "message": pass_message if ok else fail_message}


def _commands(*, config_path: str, callback_url: str, shell: str, ok: bool) -> list[str]:
    if ok:
        return [
            f"stock-agent-orchestrator beta-live-readiness-bundle --config {config_path} --callback-url {callback_url} --format markdown",
            f"stock-agent-orchestrator beta-live-runbook --config {config_path} --callback-url {callback_url} --format markdown",
            f"stock-agent-orchestrator beta-live-launch-packet --config {config_path} --callback-url {callback_url} --format markdown",
        ]
    return [
        f"stock-agent-orchestrator beta-live-intake-checklist --shell {shell} --format markdown",
        f"stock-agent-orchestrator beta-live-env-template --shell {shell}",
        f"stock-agent-orchestrator beta-live-config-status --config {config_path} --format markdown",
    ]


def _stop_conditions() -> list[str]:
    return [
        "configs/beta.live.toml 未被 .gitignore 保护时停止。",
        "任何 sensitive 字段在输出中不是 <redacted> 时停止。",
        "ready_for_preflight 为 false 时不要启动 --allow-live-send。",
        "chat_id 或 open_id 不能确认属于临时 beta 群时停止。",
    ]


def _next_steps(*, ok: bool) -> list[str]:
    if ok:
        return [
            "Run beta-live-readiness-bundle with the reviewed config.",
            "Only after readiness bundle passes, proceed to callback probe and beta group validation.",
        ]
    return [
        "Complete the missing or placeholder fields.",
        "Confirm configs/beta.live.toml is gitignored.",
        "Re-run beta-live-config-review before any real beta action.",
    ]
