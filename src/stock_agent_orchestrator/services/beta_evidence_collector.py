from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.services.beta_validation_report import (
    BetaValidationEvidence,
    BetaValidationReport,
    beta_validation_report_to_markdown,
    build_beta_validation_report,
)


@dataclass(frozen=True, slots=True)
class BetaEvidenceCollection:
    ok: bool
    healthz_url: str
    healthz_path: str
    report_path: str
    report: BetaValidationReport
    next_steps: list[str]


def collect_beta_evidence(
    *,
    config: OrchestratorConfig,
    callback_url: str,
    commit: str,
    db_path: Path,
    healthz_json_path: Path,
    report_path: Path,
    task_id: str = "",
    evidence: BetaValidationEvidence | None = None,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> BetaEvidenceCollection:
    opener = opener or urllib.request.urlopen
    base_url = callback_url.strip().rstrip("/")
    healthz_url = f"{base_url}/healthz" if base_url else ""
    if not healthz_url:
        raise ValueError("callback_url is required")

    healthz = _fetch_json(healthz_url, opener=opener)
    healthz_json_path.parent.mkdir(parents=True, exist_ok=True)
    healthz_json_path.write_text(json.dumps(healthz, ensure_ascii=False, indent=2), encoding="utf-8")

    report = build_beta_validation_report(
        config=config,
        callback_url=callback_url,
        commit=commit,
        db_path=db_path,
        task_id=task_id,
        healthz_json_path=healthz_json_path,
        evidence=evidence,
    )
    rendered = beta_validation_report_to_markdown(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(rendered, encoding="utf-8")

    return BetaEvidenceCollection(
        ok=report.ok,
        healthz_url=healthz_url,
        healthz_path=str(healthz_json_path),
        report_path=str(report_path),
        report=report,
        next_steps=_next_steps(report),
    )


def beta_evidence_collection_to_dict(collection: BetaEvidenceCollection) -> dict[str, Any]:
    return asdict(collection)


def beta_evidence_collection_to_markdown(collection: BetaEvidenceCollection) -> str:
    lines = [
        "# Beta Evidence Collection",
        "",
        f"- ok: `{str(collection.ok).lower()}`",
        f"- healthz_url: `{collection.healthz_url}`",
        f"- healthz_json: `{collection.healthz_path}`",
        f"- report: `{collection.report_path}`",
        f"- task_id: `{collection.report.task_id or '<missing>'}`",
        f"- task_card_message_id: `{collection.report.task_card_message_id or '<missing>'}`",
        "",
        "## Next Steps",
    ]
    lines.extend(f"- {step}" for step in collection.next_steps)
    return "\n".join(lines)


def _fetch_json(url: str, *, opener: Callable[[urllib.request.Request], Any]) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    with opener(request) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("healthz response must be a JSON object")
    return payload


def _next_steps(report: BetaValidationReport) -> list[str]:
    if report.ok:
        return [
            "补充 beta 群任务卡截图或录屏路径。",
            "提交 docs/BETA_VALIDATION_REPORT_ZH.md 作为申请证据。",
            "重新运行 application-readiness，确认 readiness 进入完整 ready 档。",
        ]
    return [
        "不要提交该报告作为成功证据，先修复报告中的未通过项。",
        "确认 beta 群委托已经创建 BETA 任务并写入 task_card_message_id。",
        "确认公网 /healthz 返回 gateway connected 且 operation_error_count 为 0。",
    ]
