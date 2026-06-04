from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.services.application_readiness import run_application_readiness
from stock_agent_orchestrator.services.beta_live_preflight import run_beta_live_preflight


@dataclass(frozen=True, slots=True)
class BetaValidationGuide:
    ready_for_live_beta: bool
    readiness_score: int
    readiness_band: str
    preflight_ok: bool
    missing_evidence_report: bool
    callback_url: str
    webhook_url: str
    healthz_url: str
    stage: str
    checklist: list[str]
    commands: list[str]
    evidence_to_collect: list[str]
    warnings: list[str]


def build_beta_validation_guide(
    *,
    config: OrchestratorConfig,
    callback_url: str,
    repo_root: Path,
    config_path: str = "configs/beta.live.toml",
    db_path: str = ".runtime/beta-live.db",
    healthz_json_path: str = ".runtime/healthz.json",
    report_path: str = "docs/BETA_VALIDATION_REPORT_ZH.md",
) -> BetaValidationGuide:
    readiness = run_application_readiness(repo_root)
    preflight = run_beta_live_preflight(config, callback_url=callback_url)
    missing_report = not (repo_root / report_path).exists()
    ready_for_live_beta = preflight.ok
    stage = _stage(preflight_ok=preflight.ok, missing_report=missing_report)

    return BetaValidationGuide(
        ready_for_live_beta=ready_for_live_beta,
        readiness_score=readiness.score,
        readiness_band=readiness.band,
        preflight_ok=preflight.ok,
        missing_evidence_report=missing_report,
        callback_url=preflight.callback_url,
        webhook_url=preflight.webhook_url,
        healthz_url=preflight.healthz_url,
        stage=stage,
        checklist=_checklist(preflight_ok=preflight.ok, missing_report=missing_report),
        commands=_commands(
            preflight_ok=preflight.ok,
            config_path=config_path,
            callback_url=preflight.callback_url or callback_url,
            db_path=db_path,
            healthz_json_path=healthz_json_path,
            report_path=report_path,
        ),
        evidence_to_collect=[
            "beta 群里 BOOS @小C-beta 的委托截图或录屏。",
            "同一任务卡首次出现和后续更新后的截图或录屏。",
            "/healthz JSON，需证明 gateway connected 且 operation_error_count 为 0。",
            "SQLite 中实际生成的任务 ID，例如 BETA-0001。",
        ],
        warnings=_warnings(preflight_ok=preflight.ok, missing_report=missing_report),
    )


def beta_validation_guide_to_dict(guide: BetaValidationGuide) -> dict:
    return asdict(guide)


def beta_validation_guide_to_markdown(guide: BetaValidationGuide) -> str:
    lines = [
        "# 飞书 Beta 验收向导",
        "",
        f"- 当前阶段：`{guide.stage}`",
        f"- readiness：`{guide.readiness_score}/100` `{guide.readiness_band}`",
        f"- preflight 通过：`{str(guide.preflight_ok).lower()}`",
        f"- 缺真实验证报告：`{str(guide.missing_evidence_report).lower()}`",
        f"- callback URL：`{guide.callback_url or '<missing>'}`",
        f"- webhook URL：`{guide.webhook_url or '<missing>'}`",
        f"- healthz URL：`{guide.healthz_url or '<missing>'}`",
        "",
        "## 检查清单",
        "",
    ]
    lines.extend(f"- {item}" for item in guide.checklist)
    lines.extend(["", "## 建议命令", ""])
    for command in guide.commands:
        lines.extend(["```bash", command, "```", ""])
    lines.extend(["## 需要收集的证据", ""])
    lines.extend(f"- {item}" for item in guide.evidence_to_collect)
    if guide.warnings:
        lines.extend(["", "## 风险提示", ""])
        lines.extend(f"- {item}" for item in guide.warnings)
    return "\n".join(lines).rstrip()


def _stage(*, preflight_ok: bool, missing_report: bool) -> str:
    if not preflight_ok:
        return "fix_preflight_before_live_beta"
    if missing_report:
        return "run_live_beta_and_collect_evidence"
    return "review_existing_beta_evidence"


def _checklist(*, preflight_ok: bool, missing_report: bool) -> list[str]:
    if not preflight_ok:
        return [
            "先修复 beta-live-preflight 失败项。",
            "不要启动 --allow-live-send。",
            "不要把当前结果作为申请证据。",
        ]
    result = [
        "启动 run-webhook，并显式传入 --allow-live-send。",
        "在飞书开放平台把事件订阅 callback 指向 webhook URL。",
        "在 beta 群发送一次 BOOS @小C-beta 委托。",
        "确认群里出现任务卡，并在小智/小巴后续消息后原地更新同一张卡。",
        "保存 /healthz JSON，确认 operation_error_count 为 0。",
    ]
    if missing_report:
        result.append("生成 docs/BETA_VALIDATION_REPORT_ZH.md 并提交。")
    else:
        result.append("复核现有 docs/BETA_VALIDATION_REPORT_ZH.md 是否包含最新截图和 commit。")
    return result


def _commands(
    *,
    preflight_ok: bool,
    config_path: str,
    callback_url: str,
    db_path: str,
    healthz_json_path: str,
    report_path: str,
) -> list[str]:
    if not preflight_ok:
        return [
            f"stock-agent-orchestrator beta-live-preflight --config {config_path} --callback-url {callback_url} --format markdown",
            "stock-agent-orchestrator application-readiness --format markdown",
        ]
    return [
        f"stock-agent-orchestrator beta-live-preflight --config {config_path} --callback-url {callback_url} --format markdown",
        f"stock-agent-orchestrator run-webhook --config {config_path} --db {db_path} --allow-live-send",
        f"stock-agent-orchestrator beta-callback-probe --config {config_path} --callback-url {callback_url} --format markdown",
        f"curl {callback_url.rstrip('/')}/healthz > {healthz_json_path}",
        (
            "stock-agent-orchestrator beta-validation-report "
            f"--config {config_path} "
            f"--callback-url {callback_url} "
            "--commit <git-commit> "
            f"--db {db_path} "
            "--task-id <BETA-0001> "
            f"--healthz-json {healthz_json_path} "
            "--beta-group-name <beta-group-name> "
            "--feishu-app-name <feishu-app-name> "
            "--task-card-screenshot <screenshot-or-gif-path> "
            f"--output {report_path}"
        ),
        "stock-agent-orchestrator application-readiness --format markdown",
    ]


def _warnings(*, preflight_ok: bool, missing_report: bool) -> list[str]:
    result: list[str] = []
    if not preflight_ok:
        result.append("preflight 未通过时进入真实群会放大配置错误和刷屏风险。")
    if missing_report:
        result.append("没有 docs/BETA_VALIDATION_REPORT_ZH.md 时，readiness 会停留在 80+ 档。")
    result.append("beta 阶段仍必须保持 allow_real_trading=false。")
    return result
