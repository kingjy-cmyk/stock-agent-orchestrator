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
    ("feishu.verification_token", "FEISHU_VERIFICATION_TOKEN"),
    ("feishu.encrypt_key", "FEISHU_ENCRYPT_KEY"),
)

SENSITIVE_ENV_NAMES = {
    "FEISHU_APP_SECRET",
    "FEISHU_VERIFICATION_TOKEN",
    "FEISHU_ENCRYPT_KEY",
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


def _render_config(env: Mapping[str, str]) -> str:
    rate_limit = str(env.get("FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE", "60")).strip() or "60"
    sqlite_db = str(env.get("STOCK_AGENT_SQLITE_DB", "./runtime/beta-live.db")).strip()
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
            'api_base_url = "https://open.feishu.cn"',
            f'app_id = "{_toml_escape(env["FEISHU_APP_ID"])}"',
            f'app_secret = "{_toml_escape(env["FEISHU_APP_SECRET"])}"',
            f'send_allowlist = ["{_toml_escape(env["FEISHU_GROUP_CHAT_ID"])}"]',
            f'verification_token = "{_toml_escape(env["FEISHU_VERIFICATION_TOKEN"])}"',
            f'encrypt_key = "{_toml_escape(env["FEISHU_ENCRYPT_KEY"])}"',
            f"webhook_rate_limit_per_minute = {int(rate_limit)}",
            "",
        ]
    )


def _toml_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


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
