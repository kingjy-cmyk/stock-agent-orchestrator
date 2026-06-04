from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import (
    PLACEHOLDER_VALUES,
    ConfigValidationIssue,
    flatten_config,
    load_config,
    validate_config,
    validation_to_dict,
)


REQUIRED_BETA_LIVE_FIELDS = (
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
    "feishu.verification_token",
    "feishu.encrypt_key",
)

SENSITIVE_FIELDS = {
    "feishu.app_secret",
    "feishu.verification_token",
    "feishu.encrypt_key",
}


@dataclass(frozen=True, slots=True)
class BetaLiveFieldStatus:
    field: str
    status: str
    value: str
    sensitive: bool = False


@dataclass(frozen=True, slots=True)
class BetaLiveConfigStatus:
    ok: bool
    exists: bool
    config_path: str
    gitignored: bool
    ready_for_preflight: bool
    field_statuses: list[BetaLiveFieldStatus]
    validation_issues: list[dict[str, str]]
    next_steps: list[str]


def inspect_beta_live_config(*, config_path: Path, repo_root: Path = Path(".")) -> BetaLiveConfigStatus:
    exists = config_path.exists()
    gitignored = _is_gitignored(config_path=config_path, repo_root=repo_root)
    field_statuses: list[BetaLiveFieldStatus] = []
    validation_issues: list[ConfigValidationIssue] = []

    if exists:
        try:
            config = load_config(config_path)
        except Exception as exc:
            validation_issues = [ConfigValidationIssue("error", "config", f"failed to parse config: {exc}")]
            field_statuses = [
                BetaLiveFieldStatus(field=field, status="unreadable", value="<config parse failed>", sensitive=field in SENSITIVE_FIELDS)
                for field in REQUIRED_BETA_LIVE_FIELDS
            ]
        else:
            validation_issues = validate_config(config)
            flattened = flatten_config(config)
            field_statuses = [_field_status(field, flattened.get(field)) for field in REQUIRED_BETA_LIVE_FIELDS]
    else:
        field_statuses = [
            BetaLiveFieldStatus(field=field, status="missing_config", value="<config file missing>", sensitive=field in SENSITIVE_FIELDS)
            for field in REQUIRED_BETA_LIVE_FIELDS
        ]

    ready_for_preflight = bool(
        exists
        and gitignored
        and not any(issue.severity == "error" for issue in validation_issues)
        and all(status.status == "filled" for status in field_statuses)
    )
    ok = ready_for_preflight
    return BetaLiveConfigStatus(
        ok=ok,
        exists=exists,
        config_path=str(config_path),
        gitignored=gitignored,
        ready_for_preflight=ready_for_preflight,
        field_statuses=field_statuses,
        validation_issues=validation_to_dict(validation_issues),
        next_steps=_next_steps(exists=exists, gitignored=gitignored, ready_for_preflight=ready_for_preflight),
    )


def beta_live_config_status_to_dict(status: BetaLiveConfigStatus) -> dict[str, Any]:
    return asdict(status)


def beta_live_config_status_to_markdown(status: BetaLiveConfigStatus) -> str:
    lines = [
        "# Beta Live Config Status",
        "",
        f"- ok: `{str(status.ok).lower()}`",
        f"- exists: `{str(status.exists).lower()}`",
        f"- config_path: `{status.config_path}`",
        f"- gitignored: `{str(status.gitignored).lower()}`",
        f"- ready_for_preflight: `{str(status.ready_for_preflight).lower()}`",
        "",
        "## Required Fields",
        "",
    ]
    for item in status.field_statuses:
        lines.append(f"- `{item.status}` {item.field}: {item.value}")
    lines.extend(["", "## Validation Issues", ""])
    if status.validation_issues:
        for issue in status.validation_issues:
            lines.append(f"- `{issue['severity']}` {issue['field']}: {issue['message']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {step}" for step in status.next_steps)
    return "\n".join(lines)


def _field_status(field: str, value: Any) -> BetaLiveFieldStatus:
    sensitive = field in SENSITIVE_FIELDS
    if value is None:
        return BetaLiveFieldStatus(field=field, status="missing", value="<missing>", sensitive=sensitive)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in PLACEHOLDER_VALUES:
            return BetaLiveFieldStatus(field=field, status="placeholder", value="<replace-me>", sensitive=sensitive)
        return BetaLiveFieldStatus(field=field, status="filled", value="<redacted>" if sensitive else stripped, sensitive=sensitive)
    if isinstance(value, list):
        if not value or any(str(item).strip() in PLACEHOLDER_VALUES for item in value):
            return BetaLiveFieldStatus(field=field, status="placeholder", value=json.dumps(value, ensure_ascii=False), sensitive=sensitive)
        return BetaLiveFieldStatus(field=field, status="filled", value=json.dumps(value, ensure_ascii=False), sensitive=sensitive)
    return BetaLiveFieldStatus(field=field, status="filled", value=str(value), sensitive=sensitive)


def _is_gitignored(*, config_path: Path, repo_root: Path) -> bool:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return False
    normalized = config_path.as_posix()
    try:
        relative = config_path.relative_to(repo_root).as_posix()
    except ValueError:
        relative = normalized
    entries = {
        line.strip().lstrip("/")
        for line in gitignore_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    return normalized.lstrip("/") in entries or relative.lstrip("/") in entries


def _next_steps(*, exists: bool, gitignored: bool, ready_for_preflight: bool) -> list[str]:
    if ready_for_preflight:
        return [
            "Run beta-live-preflight with the same config and callback URL.",
            "Run beta-live-runbook after preflight passes.",
        ]
    result: list[str] = []
    if not exists:
        result.append("Run init-beta-live-config --output configs/beta.live.toml.")
    if not gitignored:
        result.append("Ensure configs/beta.live.toml is listed in .gitignore before adding real secrets.")
    result.append("Replace every placeholder field before real beta validation.")
    result.append("Re-run beta-live-config-status until ready_for_preflight is true.")
    return result
