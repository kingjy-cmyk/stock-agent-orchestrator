from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.domain.models import TaskIntent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_evidence_collector import (
    BetaEvidenceCollection,
    beta_evidence_collection_to_dict,
    collect_beta_evidence,
)
from stock_agent_orchestrator.services.beta_validation_report import BetaValidationEvidence
from stock_agent_orchestrator.services.task_engine import TaskEngine


@dataclass(frozen=True, slots=True)
class BetaLiveEvidenceRehearsal:
    ok: bool
    runtime_dir: str
    callback_url: str
    config_path: str
    db_path: str
    healthz_json_path: str
    report_path: str
    task_id: str
    checks: list[dict[str, str]]
    collection: dict[str, Any]
    next_steps: list[str]


def run_beta_live_evidence_rehearsal(
    *,
    runtime_dir: Path = Path(".runtime/beta-evidence-rehearsal"),
    callback_url: str = "https://agent-beta.example.com",
    commit: str = "rehearsal-commit",
) -> BetaLiveEvidenceRehearsal:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    config_path = runtime_dir / "beta.live.rehearsal.toml"
    db_path = runtime_dir / "webhook.db"
    healthz_json_path = runtime_dir / "healthz.json"
    report_path = runtime_dir / "BETA_VALIDATION_REPORT_REHEARSAL_ZH.md"
    task_id = "BETA-REHEARSAL-0001"

    config_path.write_text(_valid_rehearsal_config(runtime_dir), encoding="utf-8")
    _write_rehearsal_task(db_path=db_path, task_id=task_id)

    collection = collect_beta_evidence(
        config=load_config(config_path),
        callback_url=callback_url,
        commit=commit,
        db_path=db_path,
        task_id=task_id,
        healthz_json_path=healthz_json_path,
        report_path=report_path,
        evidence=BetaValidationEvidence(
            beta_group_name="Stock Agent Beta Rehearsal",
            feishu_app_name="Stock Agent Rehearsal App",
            delegate_text="@小C-beta 今天先给我一份候选池",
            beta_group_screenshot="<rehearsal-only>",
            task_card_screenshot="<rehearsal-only>",
            healthz_screenshot="<rehearsal-only>",
            notes="本报告由 beta-live-evidence-rehearsal 生成，只用于本地彩排，不能作为真实飞书 beta 申请证据。",
        ),
        opener=lambda _request: _FakeHealthzResponse(_rehearsal_healthz()),
    )
    checks = _checks(collection=collection, report_path=report_path, healthz_json_path=healthz_json_path)
    ok = bool(collection.ok and report_path.exists() and healthz_json_path.exists())
    return BetaLiveEvidenceRehearsal(
        ok=ok,
        runtime_dir=str(runtime_dir),
        callback_url=callback_url,
        config_path=str(config_path),
        db_path=str(db_path),
        healthz_json_path=str(healthz_json_path),
        report_path=str(report_path),
        task_id=task_id,
        checks=checks,
        collection=beta_evidence_collection_to_dict(collection),
        next_steps=_next_steps(ok=ok),
    )


def beta_live_evidence_rehearsal_to_dict(rehearsal: BetaLiveEvidenceRehearsal) -> dict[str, Any]:
    return asdict(rehearsal)


def beta_live_evidence_rehearsal_to_markdown(rehearsal: BetaLiveEvidenceRehearsal) -> str:
    lines = [
        "# 飞书 Beta Evidence Rehearsal",
        "",
        f"- ok: `{str(rehearsal.ok).lower()}`",
        f"- runtime_dir: `{rehearsal.runtime_dir}`",
        f"- callback_url: `{rehearsal.callback_url}`",
        f"- task_id: `{rehearsal.task_id}`",
        f"- healthz_json: `{rehearsal.healthz_json_path}`",
        f"- report: `{rehearsal.report_path}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{item['status']}` {item['name']}: {item['message']}" for item in rehearsal.checks)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {step}" for step in rehearsal.next_steps)
    return "\n".join(lines)


class _FakeHealthzResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeHealthzResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _write_rehearsal_task(*, db_path: Path, task_id: str) -> None:
    store = SQLiteTaskStore(db_path)
    store.init_db()
    task = TaskEngine().create_task(
        task_id=task_id,
        title="Rehearsal daily candidate pool",
        intent=TaskIntent.DAILY_CANDIDATE_POOL,
        summary="@小C-beta 今天先给我一份候选池",
        context={
            "task_card_message_id": "om_rehearsal_task_card_1",
            "task_card_update_count": 2,
        },
    )
    store.save_task(task)


def _checks(*, collection: BetaEvidenceCollection, report_path: Path, healthz_json_path: Path) -> list[dict[str, str]]:
    return [
        _check("healthz_json_written", healthz_json_path.exists(), "healthz JSON was written", "healthz JSON was not written"),
        _check("report_written", report_path.exists(), "validation report was written", "validation report was not written"),
        _check("report_ok", collection.ok, "validation report passes", "validation report does not pass"),
    ]


def _check(name: str, ok: bool, pass_message: str, fail_message: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "message": pass_message if ok else fail_message,
    }


def _next_steps(*, ok: bool) -> list[str]:
    if ok:
        return [
            "Open the rehearsal report to understand the real evidence format.",
            "Do not commit rehearsal artifacts or treat them as real Feishu beta evidence.",
            "Fill the real beta config and run beta-live-readiness-bundle.",
            "After real beta succeeds, run collect-beta-evidence against the live callback.",
        ]
    return [
        "Fix the failed rehearsal check.",
        "Run beta-live-evidence-rehearsal again before real beta validation.",
    ]


def _rehearsal_healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "gateway": {
            "status": "connected",
            "accepted_count": 3,
            "enqueued_count": 3,
            "duplicate_count": 0,
            "operation_error_count": 0,
            "last_error": "",
        },
    }


def _valid_rehearsal_config(runtime_dir: Path) -> str:
    return f"""
[project]
name = "stock-agent-orchestrator"
environment = "beta"
mode = "active"

[roles]
owner = "xiaoc-beta"
data = "xiaozhi-beta"
analyst = "xiaoba-beta"

[automation]
auto_advance_within_rules = true
allow_real_trading = false
require_user_review_for_new_rules = true

[paths]
candidate_list = "{(runtime_dir / 'candidate_list.md').as_posix()}"
seven_layer_reports = "{(runtime_dir / 'seven_layer').as_posix()}"
entry_monitor_reports = "{(runtime_dir / 'entry_monitor').as_posix()}"
sqlite_db = "{(runtime_dir / 'beta-live.db').as_posix()}"

[feishu]
group_chat_id = "oc_beta_rehearsal_chat"
owner_open_id = "ou_owner_rehearsal"
data_open_id = "ou_data_rehearsal"
analyst_open_id = "ou_analyst_rehearsal"
send_mode = "live"
api_base_url = "https://open.feishu.cn"
app_id = "cli_a_rehearsal_app"
app_secret = "rehearsal-secret"
send_allowlist = ["oc_beta_rehearsal_chat"]
verification_token = "rehearsal-token"
encrypt_key = "rehearsal-encrypt-key"
webhook_rate_limit_per_minute = 60
"""
