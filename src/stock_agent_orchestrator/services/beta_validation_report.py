from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.domain.models import Task, TaskStatus
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_live_preflight import (
    BetaLivePreflightReport,
    preflight_report_to_dict,
    run_beta_live_preflight,
)


@dataclass(frozen=True, slots=True)
class BetaValidationEvidence:
    beta_group_name: str = ""
    feishu_app_name: str = ""
    delegate_text: str = "@小C-beta 今天先给我一份候选池"
    beta_group_screenshot: str = ""
    task_card_screenshot: str = ""
    healthz_screenshot: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class BetaValidationReport:
    ok: bool
    commit: str
    callback_url: str
    webhook_url: str
    healthz_url: str
    preflight_ok: bool
    task_found: bool
    task_card_found: bool
    healthz_ok: bool
    task_id: str = ""
    task_status: str = ""
    task_assignee: str = ""
    task_waiting_user: bool = False
    task_card_message_id: str = ""
    task_card_update_count: int = 0
    healthz: dict[str, Any] = field(default_factory=dict)
    preflight: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    conclusions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def build_beta_validation_report(
    *,
    config: OrchestratorConfig,
    callback_url: str,
    commit: str,
    db_path: Path | None = None,
    task_id: str = "",
    healthz_json_path: Path | None = None,
    evidence: BetaValidationEvidence | None = None,
) -> BetaValidationReport:
    preflight = run_beta_live_preflight(config, callback_url=callback_url)
    task = _load_task(db_path, task_id) if db_path else None
    healthz = _load_json_object(healthz_json_path) if healthz_json_path else {}
    evidence = evidence or BetaValidationEvidence()
    healthz_ok = _healthz_ok(healthz)
    task_found = task is not None
    task_card_message_id = str(task.context.get("task_card_message_id") or "") if task else ""
    task_card_update_count = int(task.context.get("task_card_update_count") or 0) if task else 0
    task_card_found = bool(task_card_message_id)
    ok = bool(preflight.ok and task_found and task_card_found and healthz_ok)

    return BetaValidationReport(
        ok=ok,
        commit=commit,
        callback_url=preflight.callback_url,
        webhook_url=preflight.webhook_url,
        healthz_url=preflight.healthz_url,
        preflight_ok=preflight.ok,
        task_found=task_found,
        task_card_found=task_card_found,
        healthz_ok=healthz_ok,
        task_id=task.task_id if task else task_id,
        task_status=task.status.value if task else "",
        task_assignee=task.current_assignee.value if task else "",
        task_waiting_user=task.status == TaskStatus.WAITING_USER if task else False,
        task_card_message_id=task_card_message_id,
        task_card_update_count=task_card_update_count,
        healthz=healthz,
        preflight=preflight_report_to_dict(preflight),
        evidence=asdict(evidence),
        conclusions=_conclusions(preflight=preflight, task=task, task_card_found=task_card_found, healthz_ok=healthz_ok),
        next_steps=_next_steps(ok=ok),
    )


def beta_validation_report_to_dict(report: BetaValidationReport) -> dict[str, Any]:
    return asdict(report)


def beta_validation_report_to_markdown(report: BetaValidationReport) -> str:
    evidence = report.evidence
    lines = [
        "# 飞书 Beta 验证报告",
        "",
        "## 基本信息",
        "",
        f"- commit：`{report.commit or '<unknown>'}`",
        f"- beta 群名称：{evidence.get('beta_group_name') or '<未填写>'}",
        f"- 飞书应用：{evidence.get('feishu_app_name') or '<未填写>'}",
        f"- callback URL：`{report.callback_url or '<missing>'}`",
        f"- webhook URL：`{report.webhook_url or '<missing>'}`",
        f"- healthz URL：`{report.healthz_url or '<missing>'}`",
        "",
        "## 验收状态",
        "",
        f"- 总体通过：`{str(report.ok).lower()}`",
        f"- preflight 通过：`{str(report.preflight_ok).lower()}`",
        f"- 任务存在：`{str(report.task_found).lower()}`",
        f"- 任务卡 message_id 存在：`{str(report.task_card_found).lower()}`",
        f"- healthz 正常：`{str(report.healthz_ok).lower()}`",
        "",
        "## 飞书群委托",
        "",
        "发送内容：",
        "",
        "```text",
        evidence.get("delegate_text") or "",
        "```",
        "",
        "结果：",
        "",
        f"- 任务 ID：`{report.task_id or '<missing>'}`",
        f"- 任务状态：`{report.task_status or '<missing>'}`",
        f"- 当前责任人：`{report.task_assignee or '<missing>'}`",
        f"- 是否等待用户：`{str(report.task_waiting_user).lower()}`",
        f"- 任务卡 message_id：`{report.task_card_message_id or '<missing>'}`",
        f"- 任务卡更新次数：`{report.task_card_update_count}`",
        "",
        "## Healthz",
        "",
        "```json",
        json.dumps(report.healthz, ensure_ascii=False, indent=2) if report.healthz else "{}",
        "```",
        "",
        "## 截图或录屏",
        "",
        f"- beta 群委托截图：{evidence.get('beta_group_screenshot') or '<未填写>'}",
        f"- 任务卡截图：{evidence.get('task_card_screenshot') or '<未填写>'}",
        f"- healthz 截图：{evidence.get('healthz_screenshot') or '<未填写>'}",
        "",
        "## 结论",
        "",
    ]
    lines.extend(f"- {item}" for item in report.conclusions)
    lines.extend(["", "## 下一步", ""])
    lines.extend(f"- {item}" for item in report.next_steps)
    notes = evidence.get("notes") or ""
    if notes:
        lines.extend(["", "## 备注", "", notes])
    return "\n".join(lines)


def _load_task(db_path: Path | None, task_id: str) -> Task | None:
    if db_path is None or not db_path.exists():
        return None
    if not task_id:
        return _latest_beta_task(db_path)
    return SQLiteTaskStore(db_path).load_task(task_id)


def _latest_beta_task(db_path: Path) -> Task | None:
    tasks = SQLiteTaskStore(db_path).list_tasks()
    for task in reversed(tasks):
        if str(task.task_id).upper().startswith("BETA-"):
            return task
    return tasks[-1] if tasks else None


def _load_json_object(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("healthz json must be an object")
    return payload


def _healthz_ok(healthz: dict[str, Any]) -> bool:
    if not healthz:
        return False
    gateway = healthz.get("gateway") if isinstance(healthz.get("gateway"), dict) else {}
    return bool(
        healthz.get("ok") is True
        and str(gateway.get("status") or "") == "connected"
        and int(gateway.get("operation_error_count") or 0) == 0
    )


def _conclusions(*, preflight: BetaLivePreflightReport, task: Task | None, task_card_found: bool, healthz_ok: bool) -> list[str]:
    result: list[str] = []
    result.append("preflight 已通过。" if preflight.ok else "preflight 未通过，不能作为真实 beta 成功证据。")
    result.append("任务已在数据库中找到。" if task else "未找到任务记录，需要确认 beta 群任务卡是否真正落库。")
    result.append("任务卡 message_id 已落库。" if task_card_found else "任务卡 message_id 未落库，不能证明群里出现了可追踪任务卡。")
    result.append("healthz 正常且无 operation error。" if healthz_ok else "healthz 未证明服务处于正常 connected 状态。")
    return result


def _next_steps(*, ok: bool) -> list[str]:
    if ok:
        return [
            "补充 beta 群任务卡截图或录屏。",
            "将该报告提交到仓库，作为申请 Codex 官方活动的验证证据。",
            "进入 Stage 3：同一任务的后续状态更新和任务卡更新。",
        ]
    return [
        "先修复未通过项，不要把该报告作为申请证据。",
        "确认 beta-live-preflight 通过。",
        "确认 beta 群任务卡出现并写入 SQLite。",
        "确认任务 context 中存在 task_card_message_id。",
        "保存 /healthz JSON，并重新生成报告。",
    ]
