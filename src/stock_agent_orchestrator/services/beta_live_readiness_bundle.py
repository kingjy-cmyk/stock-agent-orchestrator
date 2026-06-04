from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.application_readiness import (
    readiness_report_to_dict,
    run_application_readiness,
)
from stock_agent_orchestrator.services.beta_live_config_status import (
    beta_live_config_status_to_dict,
    inspect_beta_live_config,
)
from stock_agent_orchestrator.services.beta_live_launch_packet import (
    beta_live_launch_packet_to_dict,
    build_beta_live_launch_packet,
)
from stock_agent_orchestrator.services.beta_live_preflight import (
    preflight_report_to_dict,
    run_beta_live_preflight,
)
from stock_agent_orchestrator.services.beta_live_prep_dry_run import (
    beta_live_prep_dry_run_to_dict,
    run_beta_live_prep_dry_run,
)
from stock_agent_orchestrator.services.beta_live_runbook import (
    beta_live_runbook_to_dict,
    build_beta_live_runbook,
)


@dataclass(frozen=True, slots=True)
class BetaLiveReadinessBundle:
    ok: bool
    stage: str
    callback_url: str
    config_path: str
    readiness_score: int
    readiness_band: str
    dry_run_ok: bool
    config_ready: bool
    preflight_ok: bool
    runbook_ready: bool
    launch_ready: bool
    missing_real_beta_evidence: bool
    checks: list[dict[str, str]]
    next_steps: list[str]
    readiness: dict[str, Any]
    dry_run: dict[str, Any]
    config_status: dict[str, Any]
    preflight: dict[str, Any] | None
    runbook: dict[str, Any] | None
    launch_packet: dict[str, Any] | None


def build_beta_live_readiness_bundle(
    *,
    repo_root: Path,
    config_path: Path,
    callback_url: str,
    db_path: str = ".runtime/webhook.db",
    healthz_json_path: str = ".runtime/healthz.json",
    report_path: str = "docs/BETA_VALIDATION_REPORT_ZH.md",
) -> BetaLiveReadinessBundle:
    readiness = run_application_readiness(repo_root)
    dry_run = run_beta_live_prep_dry_run(callback_url=callback_url)
    config_status = inspect_beta_live_config(config_path=config_path, repo_root=repo_root)
    preflight = None
    runbook = None
    launch_packet = None
    preflight_ok = False
    runbook_ready = False
    launch_ready = False

    if config_status.ready_for_preflight:
        config = load_config(config_path)
        preflight = run_beta_live_preflight(config, callback_url=callback_url)
        runbook = build_beta_live_runbook(
            config=config,
            callback_url=callback_url,
            repo_root=repo_root,
            config_path=str(config_path),
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
        )
        launch_packet = build_beta_live_launch_packet(
            config=config,
            callback_url=callback_url,
            repo_root=repo_root,
            config_path=str(config_path),
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
        )
        preflight_ok = preflight.ok
        runbook_ready = runbook.ready_to_start
        launch_ready = launch_packet.ready_to_launch

    missing_real_beta_evidence = not (repo_root / report_path).exists()
    ok = bool(dry_run.ok and config_status.ready_for_preflight and preflight_ok and runbook_ready and launch_ready)
    stage = _stage(
        dry_run_ok=dry_run.ok,
        config_ready=config_status.ready_for_preflight,
        preflight_ok=preflight_ok,
        runbook_ready=runbook_ready,
        launch_ready=launch_ready,
        missing_real_beta_evidence=missing_real_beta_evidence,
    )
    checks = _checks(
        dry_run_ok=dry_run.ok,
        config_ready=config_status.ready_for_preflight,
        preflight_ok=preflight_ok,
        runbook_ready=runbook_ready,
        launch_ready=launch_ready,
        missing_real_beta_evidence=missing_real_beta_evidence,
    )

    return BetaLiveReadinessBundle(
        ok=ok,
        stage=stage,
        callback_url=callback_url,
        config_path=str(config_path),
        readiness_score=readiness.score,
        readiness_band=readiness.band,
        dry_run_ok=dry_run.ok,
        config_ready=config_status.ready_for_preflight,
        preflight_ok=preflight_ok,
        runbook_ready=runbook_ready,
        launch_ready=launch_ready,
        missing_real_beta_evidence=missing_real_beta_evidence,
        checks=checks,
        next_steps=_next_steps(stage=stage),
        readiness=readiness_report_to_dict(readiness),
        dry_run=beta_live_prep_dry_run_to_dict(dry_run),
        config_status=beta_live_config_status_to_dict(config_status),
        preflight=preflight_report_to_dict(preflight) if preflight else None,
        runbook=beta_live_runbook_to_dict(runbook) if runbook else None,
        launch_packet=beta_live_launch_packet_to_dict(launch_packet) if launch_packet else None,
    )


def beta_live_readiness_bundle_to_dict(bundle: BetaLiveReadinessBundle) -> dict[str, Any]:
    return asdict(bundle)


def beta_live_readiness_bundle_to_markdown(bundle: BetaLiveReadinessBundle) -> str:
    lines = [
        "# 飞书 Beta Live Readiness Bundle",
        "",
        f"- ok: `{str(bundle.ok).lower()}`",
        f"- stage: `{bundle.stage}`",
        f"- readiness: `{bundle.readiness_score}/100` `{bundle.readiness_band}`",
        f"- callback_url: `{bundle.callback_url}`",
        f"- config_path: `{bundle.config_path}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{item['status']}` {item['name']}: {item['message']}" for item in bundle.checks)
    lines.extend(["", "## Gate Summary"])
    lines.extend(
        [
            f"- dry_run_ok: `{str(bundle.dry_run_ok).lower()}`",
            f"- config_ready: `{str(bundle.config_ready).lower()}`",
            f"- preflight_ok: `{str(bundle.preflight_ok).lower()}`",
            f"- runbook_ready: `{str(bundle.runbook_ready).lower()}`",
            f"- launch_ready: `{str(bundle.launch_ready).lower()}`",
            f"- missing_real_beta_evidence: `{str(bundle.missing_real_beta_evidence).lower()}`",
        ]
    )
    if bundle.launch_packet:
        values = bundle.launch_packet.get("feishu_console_values", {})
        lines.extend(["", "## Feishu Console Values"])
        for key, value in values.items():
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {step}" for step in bundle.next_steps)
    return "\n".join(lines)


def _stage(
    *,
    dry_run_ok: bool,
    config_ready: bool,
    preflight_ok: bool,
    runbook_ready: bool,
    launch_ready: bool,
    missing_real_beta_evidence: bool,
) -> str:
    if not dry_run_ok:
        return "fix_local_preparation_chain"
    if not config_ready:
        return "fill_real_beta_config"
    if not preflight_ok:
        return "fix_real_beta_preflight"
    if not runbook_ready:
        return "fix_real_beta_runbook"
    if not launch_ready:
        return "fix_real_beta_launch_packet"
    if missing_real_beta_evidence:
        return "ready_for_real_beta_group_validation"
    return "review_existing_beta_evidence"


def _checks(
    *,
    dry_run_ok: bool,
    config_ready: bool,
    preflight_ok: bool,
    runbook_ready: bool,
    launch_ready: bool,
    missing_real_beta_evidence: bool,
) -> list[dict[str, str]]:
    return [
        _check("dry_run", dry_run_ok, "local beta preparation chain passes", "local beta preparation chain failed"),
        _check("config_status", config_ready, "real config is filled and gitignored", "real config is missing, unsafe, or incomplete"),
        _check("preflight", preflight_ok, "real beta preflight passes", "real beta preflight has not passed"),
        _check("runbook", runbook_ready, "runbook allows live beta start", "runbook does not allow live beta start"),
        _check("launch_packet", launch_ready, "launch packet is ready", "launch packet is not ready"),
        _check(
            "real_beta_evidence",
            not missing_real_beta_evidence,
            "real beta validation report exists",
            "real beta validation report is still missing",
        ),
    ]


def _check(name: str, ok: bool, pass_message: str, fail_message: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "message": pass_message if ok else fail_message,
    }


def _next_steps(*, stage: str) -> list[str]:
    if stage == "fix_local_preparation_chain":
        return ["Run beta-live-prep-dry-run and fix the failed local preparation step."]
    if stage == "fill_real_beta_config":
        return [
            "Fill configs/beta.live.toml from real Feishu beta values or run beta-live-config-from-env.",
            "Run beta-live-config-status until ready_for_preflight is true.",
        ]
    if stage == "fix_real_beta_preflight":
        return ["Run beta-live-preflight and fix every failed check before touching the beta group."]
    if stage == "fix_real_beta_runbook":
        return ["Run beta-live-runbook and follow its stop conditions."]
    if stage == "fix_real_beta_launch_packet":
        return ["Run beta-live-launch-packet and fix beta group isolation or launch gates."]
    if stage == "ready_for_real_beta_group_validation":
        return [
            "Start run-webhook with --allow-live-send.",
            "Run beta-callback-probe.",
            "Configure Feishu event subscription callback.",
            "Send the beta group test message and capture task-card evidence.",
            "Run collect-beta-evidence to generate docs/BETA_VALIDATION_REPORT_ZH.md.",
        ]
    return ["Review docs/BETA_VALIDATION_REPORT_ZH.md and rerun application-readiness."]
