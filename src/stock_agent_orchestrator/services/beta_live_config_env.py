from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from stock_agent_orchestrator.services.beta_live_config_status import inspect_beta_live_config


ENV_FIELDS: tuple[tuple[str, str], ...] = (
    ("paths.candidate_list", "STOCK_AGENT_CANDIDATE_LIST"),
    ("paths.seven_layer_reports", "STOCK_AGENT_SEVEN_LAYER_REPORTS"),
    ("paths.entry_monitor_reports", "STOCK_AGENT_ENTRY_MONITOR_REPORTS"),
    ("paths.sqlite_db", "STOCK_AGENT_SQLITE_DB"),
    ("feishu.group_chat_id", "FEISHU_GROUP_CHAT_ID"),
    ("feishu.owner_open_id", "FEISHU_OWNER_OPEN_ID"),
    ("feishu.data_open_id", "FEISHU_DATA_OPEN_ID"),
    ("feishu.analyst_open_id", "FEISHU_ANALYST_OPEN_ID"),
    ("feishu.app_id", "FEISHU_APP_ID"),
    ("feishu.app_secret", "FEISHU_APP_SECRET"),
)

SENSITIVE_ENV_NAMES = {
    "FEISHU_APP_SECRET",
    "FEISHU_VERIFICATION_TOKEN",
    "FEISHU_ENCRYPT_KEY",
}

ENV_DEFAULTS = {
    "STOCK_AGENT_CANDIDATE_LIST": "C:\\path\\to\\candidate_list.md",
    "STOCK_AGENT_SEVEN_LAYER_REPORTS": "C:\\path\\to\\seven_layer",
    "STOCK_AGENT_ENTRY_MONITOR_REPORTS": "C:\\path\\to\\entry_monitor",
    "STOCK_AGENT_SQLITE_DB": "./runtime/beta-live.db",
    "FEISHU_GROUP_CHAT_ID": "oc_xxx",
    "FEISHU_OWNER_OPEN_ID": "ou_xiaoc_beta",
    "FEISHU_DATA_OPEN_ID": "ou_xiaozhi_beta",
    "FEISHU_ANALYST_OPEN_ID": "ou_xiaoba_beta",
    "FEISHU_APP_ID": "cli_xxx",
    "FEISHU_APP_SECRET": "<secret>",
    "FEISHU_EVENT_MODE": "long_connection",
    "FEISHU_VERIFICATION_TOKEN": "<token>",
    "FEISHU_ENCRYPT_KEY": "<encrypt-key>",
    "FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE": "60",
}

LOCAL_ENV_DEFAULTS = {
    **ENV_DEFAULTS,
    "STOCK_AGENT_CANDIDATE_LIST": "\\\\wsl.localhost\\Ubuntu\\home\\jy95\\.openclaw\\evolution\\shared\\recurring\\candidate_list.md",
    "STOCK_AGENT_SEVEN_LAYER_REPORTS": ".runtime/beta-live/seven_layer",
    "STOCK_AGENT_ENTRY_MONITOR_REPORTS": ".runtime/beta-live/entry_monitor",
    "STOCK_AGENT_SQLITE_DB": ".runtime/beta-live.db",
}

BASH_LOCAL_ENV_DEFAULTS = {
    **LOCAL_ENV_DEFAULTS,
    "STOCK_AGENT_CANDIDATE_LIST": "/home/jy95/.openclaw/evolution/shared/recurring/candidate_list.md",
}


@dataclass(frozen=True, slots=True)
class BetaLiveConfigFromEnvResult:
    written: bool
    output_path: str
    missing_env: list[str]
    gitignored: bool
    ready_for_preflight: bool
    next_steps: list[str]
    warnings: list[str]


def write_beta_live_config_from_env(
    *,
    output_path: Path,
    repo_root: Path = Path("."),
    env: Mapping[str, str] | None = None,
    overwrite: bool = False,
) -> BetaLiveConfigFromEnvResult:
    env = env or os.environ
    missing = [env_name for _field, env_name in ENV_FIELDS if not str(env.get(env_name, "")).strip()]
    status_before = inspect_beta_live_config(config_path=output_path, repo_root=repo_root)
    if missing:
        return BetaLiveConfigFromEnvResult(
            written=False,
            output_path=str(output_path),
            missing_env=missing,
            gitignored=status_before.gitignored,
            ready_for_preflight=False,
            next_steps=_next_steps(written=False),
            warnings=[
                "No file was written because required environment variables are missing.",
                "Secret values are read from environment variables and are never printed by this command.",
            ],
        )
    if not status_before.gitignored:
        return BetaLiveConfigFromEnvResult(
            written=False,
            output_path=str(output_path),
            missing_env=[],
            gitignored=False,
            ready_for_preflight=False,
            next_steps=[
                "Add configs/beta.live.toml to .gitignore before writing real secrets.",
                "Re-run beta-live-config-from-env after gitignore protection is in place.",
            ],
            warnings=["No file was written because the output path is not gitignored."],
        )
    if output_path.exists() and not overwrite:
        return BetaLiveConfigFromEnvResult(
            written=False,
            output_path=str(output_path),
            missing_env=[],
            gitignored=True,
            ready_for_preflight=status_before.ready_for_preflight,
            next_steps=[
                "Existing config was not overwritten.",
                "Pass --overwrite if you intentionally want to regenerate configs/beta.live.toml from environment variables.",
                f"Run: stock-agent-orchestrator beta-live-config-status --config {output_path} --format markdown",
            ],
            warnings=["No file was written because output already exists."],
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_config(env), encoding="utf-8")
    status_after = inspect_beta_live_config(config_path=output_path, repo_root=repo_root)
    return BetaLiveConfigFromEnvResult(
        written=True,
        output_path=str(output_path),
        missing_env=[],
        gitignored=status_after.gitignored,
        ready_for_preflight=status_after.ready_for_preflight,
        next_steps=_next_steps(written=True),
        warnings=[
            "Real secrets were written to the local ignored config file.",
            "Do not commit configs/beta.live.toml.",
        ],
    )


def beta_live_config_from_env_to_dict(result: BetaLiveConfigFromEnvResult) -> dict:
    return asdict(result)


def beta_live_config_from_env_to_markdown(result: BetaLiveConfigFromEnvResult) -> str:
    lines = [
        "# Beta Live Config From Env",
        "",
        f"- written: `{str(result.written).lower()}`",
        f"- output_path: `{result.output_path}`",
        f"- gitignored: `{str(result.gitignored).lower()}`",
        f"- ready_for_preflight: `{str(result.ready_for_preflight).lower()}`",
        "",
        "## Missing Environment Variables",
        "",
    ]
    if result.missing_env:
        lines.extend(f"- `{env_name}`" for env_name in result.missing_env)
    else:
        lines.append("- none")
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {step}" for step in result.next_steps)
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)


def render_beta_live_env_template(*, shell: str = "powershell", use_local_defaults: bool = False) -> str:
    normalized = shell.strip().lower()
    if normalized not in {"powershell", "bash"}:
        raise ValueError("shell must be powershell or bash")
    defaults = _env_defaults(shell=normalized, use_local_defaults=use_local_defaults)
    lines = [
        "# Fill these values, then run:",
        "# stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown",
        "",
    ]
    if use_local_defaults:
        lines.extend(
            [
                "# Local defaults enabled:",
                "# - candidate_list points to the current OpenClaw shared recurring file.",
                "# - report and database paths point to this repo's ignored .runtime directory.",
                "",
            ]
        )
    for _field, env_name in ENV_FIELDS:
        lines.append(_env_line(shell=normalized, env_name=env_name, value=defaults[env_name]))
    lines.append(_env_line(shell=normalized, env_name="FEISHU_EVENT_MODE", value=defaults["FEISHU_EVENT_MODE"]))
    lines.append(_env_line(shell=normalized, env_name="FEISHU_VERIFICATION_TOKEN", value=defaults["FEISHU_VERIFICATION_TOKEN"]))
    lines.append(_env_line(shell=normalized, env_name="FEISHU_ENCRYPT_KEY", value=defaults["FEISHU_ENCRYPT_KEY"]))
    lines.append(_env_line(shell=normalized, env_name="FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE", value=defaults["FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE"]))
    return "\n".join(lines)


def _render_config(env: Mapping[str, str]) -> str:
    rate_limit = str(env.get("FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE", "60")).strip() or "60"
    sqlite_db = str(env.get("STOCK_AGENT_SQLITE_DB", "./runtime/beta-live.db")).strip()
    event_mode = str(env.get("FEISHU_EVENT_MODE", "long_connection")).strip() or "long_connection"
    verification_token = str(env.get("FEISHU_VERIFICATION_TOKEN", "")).strip()
    encrypt_key = str(env.get("FEISHU_ENCRYPT_KEY", "")).strip()
    return "\n".join(
        [
            "[project]",
            'name = "stock-agent-orchestrator"',
            'environment = "beta"',
            'mode = "active"',
            "",
            "[roles]",
            'owner = "xiaoc-beta"',
            'data = "xiaozhi-beta"',
            'analyst = "xiaoba-beta"',
            "",
            "[automation]",
            "auto_advance_within_rules = true",
            "allow_real_trading = false",
            "require_user_review_for_new_rules = true",
            "",
            "[paths]",
            f'candidate_list = "{_toml_escape(env["STOCK_AGENT_CANDIDATE_LIST"])}"',
            f'seven_layer_reports = "{_toml_escape(env["STOCK_AGENT_SEVEN_LAYER_REPORTS"])}"',
            f'entry_monitor_reports = "{_toml_escape(env["STOCK_AGENT_ENTRY_MONITOR_REPORTS"])}"',
            f'sqlite_db = "{_toml_escape(sqlite_db)}"',
            "",
            "[feishu]",
            f'group_chat_id = "{_toml_escape(env["FEISHU_GROUP_CHAT_ID"])}"',
            f'owner_open_id = "{_toml_escape(env["FEISHU_OWNER_OPEN_ID"])}"',
            f'data_open_id = "{_toml_escape(env["FEISHU_DATA_OPEN_ID"])}"',
            f'analyst_open_id = "{_toml_escape(env["FEISHU_ANALYST_OPEN_ID"])}"',
            'send_mode = "live"',
            f'event_mode = "{_toml_escape(event_mode)}"',
            'api_base_url = "https://open.feishu.cn"',
            f'app_id = "{_toml_escape(env["FEISHU_APP_ID"])}"',
            f'app_secret = "{_toml_escape(env["FEISHU_APP_SECRET"])}"',
            f'send_allowlist = ["{_toml_escape(env["FEISHU_GROUP_CHAT_ID"])}"]',
            f'verification_token = "{_toml_escape(verification_token)}"',
            f'encrypt_key = "{_toml_escape(encrypt_key)}"',
            f"webhook_rate_limit_per_minute = {int(rate_limit)}",
            "",
        ]
    )


def _toml_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _env_line(*, shell: str, env_name: str, value: str) -> str:
    escaped = _shell_escape(value=value, shell=shell)
    if shell == "powershell":
        return f'$env:{env_name}="{escaped}"'
    return f'export {env_name}="{escaped}"'


def _env_defaults(*, shell: str, use_local_defaults: bool) -> Mapping[str, str]:
    if not use_local_defaults:
        return ENV_DEFAULTS
    if shell == "bash":
        return BASH_LOCAL_ENV_DEFAULTS
    return LOCAL_ENV_DEFAULTS


def _shell_escape(*, value: str, shell: str) -> str:
    if shell == "powershell":
        return value.replace("`", "``").replace('"', '`"')
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")


def _next_steps(*, written: bool) -> list[str]:
    if written:
        return [
            "Run beta-live-config-status to confirm fields are filled and secrets are redacted.",
            "Run beta-live-preflight with your public callback URL.",
            "Run beta-live-runbook after preflight passes.",
        ]
    return [
        "Set the missing environment variables.",
        "Re-run beta-live-config-from-env.",
    ]
