from __future__ import annotations

import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.beta_live_config_env import write_beta_live_config_from_env
from stock_agent_orchestrator.services.beta_live_config_status import (
    beta_live_config_status_to_dict,
    inspect_beta_live_config,
)
from stock_agent_orchestrator.services.beta_live_preflight import (
    preflight_report_to_dict,
    run_beta_live_preflight,
)
from stock_agent_orchestrator.services.beta_live_runbook import (
    beta_live_runbook_to_dict,
    build_beta_live_runbook,
)


@dataclass(frozen=True, slots=True)
class BetaLivePrepDryRun:
    ok: bool
    callback_url: str
    config_written: bool
    config_ready: bool
    preflight_ok: bool
    runbook_ready: bool
    checks: list[str]
    config_status: dict[str, Any]
    preflight: dict[str, Any]
    runbook: dict[str, Any]
    next_steps: list[str]


def run_beta_live_prep_dry_run(*, callback_url: str = "https://agent-beta.example.com") -> BetaLivePrepDryRun:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config_path = root / "configs" / "beta.live.toml"
        (root / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")
        config_result = write_beta_live_config_from_env(
            output_path=config_path,
            repo_root=root,
            env=_fake_env(root),
            overwrite=True,
        )
        config_status = inspect_beta_live_config(config_path=config_path, repo_root=root)
        config = load_config(config_path)
        preflight = run_beta_live_preflight(config, callback_url=callback_url)
        runbook = build_beta_live_runbook(
            config=config,
            callback_url=callback_url,
            repo_root=root,
            config_path=str(config_path),
            db_path=str(root / ".runtime" / "webhook.db"),
            healthz_json_path=str(root / ".runtime" / "healthz.json"),
            report_path=str(root / "docs" / "BETA_VALIDATION_REPORT_ZH.md"),
        )
        checks = [
            f"config_written={str(config_result.written).lower()}",
            f"config_ready={str(config_status.ready_for_preflight).lower()}",
            f"preflight_ok={str(preflight.ok).lower()}",
            f"runbook_ready={str(runbook.ready_to_start).lower()}",
        ]
        ok = bool(config_result.written and config_status.ready_for_preflight and preflight.ok and runbook.ready_to_start)
        return BetaLivePrepDryRun(
            ok=ok,
            callback_url=callback_url,
            config_written=config_result.written,
            config_ready=config_status.ready_for_preflight,
            preflight_ok=preflight.ok,
            runbook_ready=runbook.ready_to_start,
            checks=checks,
            config_status=beta_live_config_status_to_dict(config_status),
            preflight=preflight_report_to_dict(preflight),
            runbook=beta_live_runbook_to_dict(runbook),
            next_steps=_next_steps(ok=ok),
        )


def beta_live_prep_dry_run_to_dict(report: BetaLivePrepDryRun) -> dict[str, Any]:
    return asdict(report)


def beta_live_prep_dry_run_to_markdown(report: BetaLivePrepDryRun) -> str:
    lines = [
        "# Beta Live Prep Dry Run",
        "",
        f"- ok: `{str(report.ok).lower()}`",
        f"- callback_url: `{report.callback_url}`",
        f"- config_written: `{str(report.config_written).lower()}`",
        f"- config_ready: `{str(report.config_ready).lower()}`",
        f"- preflight_ok: `{str(report.preflight_ok).lower()}`",
        f"- runbook_ready: `{str(report.runbook_ready).lower()}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{check}`" for check in report.checks)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {step}" for step in report.next_steps)
    return "\n".join(lines)


def _fake_env(root: Path) -> dict[str, str]:
    return {
        "STOCK_AGENT_CANDIDATE_LIST": str(root / "runtime" / "candidate_list.md"),
        "STOCK_AGENT_SEVEN_LAYER_REPORTS": str(root / "runtime" / "seven_layer"),
        "STOCK_AGENT_ENTRY_MONITOR_REPORTS": str(root / "runtime" / "entry_monitor"),
        "STOCK_AGENT_SQLITE_DB": str(root / "runtime" / "beta-live.db"),
        "FEISHU_GROUP_CHAT_ID": "oc_beta_chat",
        "FEISHU_OWNER_OPEN_ID": "ou_owner",
        "FEISHU_DATA_OPEN_ID": "ou_data",
        "FEISHU_ANALYST_OPEN_ID": "ou_analyst",
        "FEISHU_APP_ID": "cli_a_dry_run_app",
        "FEISHU_APP_SECRET": "dry-run-secret",
        "FEISHU_VERIFICATION_TOKEN": "dry-run-token",
        "FEISHU_ENCRYPT_KEY": "dry-run-encrypt-key",
        "FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE": "60",
    }


def _next_steps(*, ok: bool) -> list[str]:
    if ok:
        return [
            "Fill real beta environment variables or configs/beta.live.toml.",
            "Run beta-live-config-status against the real local config.",
            "Run beta-live-preflight with the real public callback URL.",
        ]
    return [
        "Fix the failed dry-run check before real beta preparation.",
        "Run beta-live-prep-dry-run again.",
    ]
