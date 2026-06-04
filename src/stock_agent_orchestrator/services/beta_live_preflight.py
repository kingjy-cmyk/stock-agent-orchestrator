from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from stock_agent_orchestrator.config import (
    PLACEHOLDER_VALUES,
    OrchestratorConfig,
    config_to_dict,
    flatten_config,
    validate_config,
    validation_to_dict,
)


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class BetaLivePreflightReport:
    ok: bool
    checks: list[PreflightCheck]
    callback_url: str
    webhook_url: str
    healthz_url: str
    config: dict
    config_issues: list[dict[str, str]]
    next_steps: list[str]


def run_beta_live_preflight(config: OrchestratorConfig, *, callback_url: str) -> BetaLivePreflightReport:
    checks: list[PreflightCheck] = []
    config_issues = validate_config(config)

    _add_check(
        checks,
        "config_validation",
        not any(issue.severity == "error" for issue in config_issues),
        "config has no validation errors",
        "config has validation errors",
    )
    _add_check(
        checks,
        "beta_active",
        config.project.environment == "beta" and config.project.mode == "active",
        "project is beta active",
        "project must be beta active before live Feishu validation",
    )
    _add_check(
        checks,
        "live_send_mode",
        config.feishu.send_mode == "live",
        "feishu.send_mode is live",
        "feishu.send_mode must be live for beta live preflight",
    )
    _add_check(
        checks,
        "send_allowlist",
        config.feishu.group_chat_id.strip() in {chat_id.strip() for chat_id in config.feishu.send_allowlist},
        "group_chat_id is in send_allowlist",
        "group_chat_id must be listed in feishu.send_allowlist",
    )
    _add_check(
        checks,
        "no_real_trading",
        not config.automation.allow_real_trading,
        "real trading is disabled",
        "real trading must stay disabled during beta validation",
    )
    _add_check(
        checks,
        "new_rule_review",
        config.automation.require_user_review_for_new_rules,
        "new rules require user review",
        "new rules must require user review",
    )

    placeholder_fields = _required_placeholder_fields(config)
    checks.append(
        PreflightCheck(
            name="no_required_placeholders",
            status="pass" if not placeholder_fields else "fail",
            message=(
                "required beta live fields have no placeholders"
                if not placeholder_fields
                else f"replace placeholders before beta live: {', '.join(placeholder_fields)}"
            ),
        )
    )

    callback = callback_url.strip().rstrip("/")
    callback_ok, callback_message = _validate_callback_url(callback)
    checks.append(
        PreflightCheck(
            name="callback_url",
            status="pass" if callback_ok else "fail",
            message=callback_message,
        )
    )

    db_parent = Path(config.paths.sqlite_db).expanduser().parent
    _add_check(
        checks,
        "sqlite_db_parent",
        bool(str(db_parent)),
        f"sqlite db parent is {db_parent}",
        "sqlite_db must include a parent directory",
    )

    ok = all(check.status == "pass" for check in checks)
    return BetaLivePreflightReport(
        ok=ok,
        checks=checks,
        callback_url=callback,
        webhook_url=f"{callback}/webhook" if callback else "",
        healthz_url=f"{callback}/healthz" if callback else "",
        config=config_to_dict(config),
        config_issues=validation_to_dict(config_issues),
        next_steps=_next_steps(ok),
    )


def preflight_report_to_dict(report: BetaLivePreflightReport) -> dict:
    return asdict(report)


def preflight_report_to_markdown(report: BetaLivePreflightReport) -> str:
    lines = [
        "# Feishu Beta Live Preflight",
        "",
        f"- ok: `{str(report.ok).lower()}`",
        f"- callback_url: `{report.callback_url or '<missing>'}`",
        f"- webhook_url: `{report.webhook_url or '<missing>'}`",
        f"- healthz_url: `{report.healthz_url or '<missing>'}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- `{check.status}` {check.name}: {check.message}")
    lines.extend(["", "## Next Steps"])
    for step in report.next_steps:
        lines.append(f"- {step}")
    return "\n".join(lines)


def _add_check(checks: list[PreflightCheck], name: str, passed: bool, pass_message: str, fail_message: str) -> None:
    checks.append(PreflightCheck(name=name, status="pass" if passed else "fail", message=pass_message if passed else fail_message))


def _required_placeholder_fields(config: OrchestratorConfig) -> list[str]:
    required = {
        "paths.candidate_list",
        "paths.seven_layer_reports",
        "paths.entry_monitor_reports",
        "paths.sqlite_db",
        "feishu.group_chat_id",
        "feishu.owner_open_id",
        "feishu.data_open_id",
        "feishu.analyst_open_id",
        "feishu.app_id",
        "feishu.app_secret",
    }
    fields = flatten_config(config)
    result: list[str] = []
    for field in sorted(required):
        value = fields.get(field)
        if isinstance(value, str) and value.strip() in PLACEHOLDER_VALUES:
            result.append(field)
    return result


def _validate_callback_url(callback_url: str) -> tuple[bool, str]:
    if not callback_url:
        return False, "callback URL is required"
    parsed = urlparse(callback_url)
    if parsed.scheme != "https":
        return False, "callback URL must be public https"
    if not parsed.netloc:
        return False, "callback URL must include host"
    return True, "callback URL is public https"


def _next_steps(ok: bool) -> list[str]:
    if not ok:
        return [
            "Fix failed checks before touching the real Feishu beta group.",
            "Run beta-live-preflight again with the same config and callback URL.",
        ]
    return [
        "Start run-webhook with the same config and --allow-live-send.",
        "Configure Feishu event subscription callback to the reported webhook_url.",
        "Send one beta group @小C-beta delegation and verify a task card appears.",
        "Check healthz after the message; duplicate_count and operation_error_count should stay controlled.",
    ]
