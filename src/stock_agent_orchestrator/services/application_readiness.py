from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    name: str
    weight: int
    passed: bool
    evidence: str
    missing: str = ""


@dataclass(frozen=True, slots=True)
class ApplicationReadinessReport:
    score: int
    max_score: int
    percent: float
    band: str
    checks: list[ReadinessCheck]
    blockers: list[str]
    next_steps: list[str]


def run_application_readiness(repo_root: Path) -> ApplicationReadinessReport:
    root = repo_root.resolve()
    checks = [
        _file_check(root, "license", 8, "LICENSE"),
        _file_check(root, "packaging", 8, "pyproject.toml"),
        _all_files_check(
            root,
            "core_docs",
            14,
            ["README.md", "docs/INTRO_ZH.md", "docs/INSTALL_ZH.md", "docs/PREREQUISITES_ZH.md", "docs/ROADMAP_ZH.md"],
        ),
        _all_files_check(
            root,
            "demo_and_cli_docs",
            12,
            ["docs/DEMO_SCRIPT_ZH.md", "docs/BETA_LIVE_PREFLIGHT_ZH.md", "docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md"],
        ),
        _dir_has_files_check(root, "tests", 12, "tests", "test_*.py"),
        _all_files_check(
            root,
            "feishu_connector",
            16,
            [
                "src/stock_agent_orchestrator/connectors/feishu.py",
                "src/stock_agent_orchestrator/connectors/feishu_webhook.py",
                "src/stock_agent_orchestrator/connectors/feishu_http.py",
                "docs/CODEX_FEISHU_PARITY_ZH.md",
            ],
        ),
        _all_files_check(
            root,
            "application_materials",
            12,
            ["docs/APPLICATION_ZH.md", "docs/DEMO_SCRIPT_ZH.md", "docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md"],
        ),
        _file_check(root, "real_beta_validation_evidence", 18, "docs/BETA_VALIDATION_REPORT_ZH.md"),
    ]
    score = sum(check.weight for check in checks if check.passed)
    max_score = sum(check.weight for check in checks)
    percent = round(score / max_score * 100, 1) if max_score else 0.0
    blockers = [check.missing for check in checks if not check.passed and check.missing]
    return ApplicationReadinessReport(
        score=score,
        max_score=max_score,
        percent=percent,
        band=_band(percent),
        checks=checks,
        blockers=blockers,
        next_steps=_next_steps(blockers),
    )


def readiness_report_to_dict(report: ApplicationReadinessReport) -> dict:
    return asdict(report)


def readiness_report_to_markdown(report: ApplicationReadinessReport) -> str:
    lines = [
        "# Application Readiness",
        "",
        f"- score: `{report.score}/{report.max_score}`",
        f"- percent: `{report.percent}%`",
        f"- band: `{report.band}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        status = "pass" if check.passed else "fail"
        lines.append(f"- `{status}` {check.name} ({check.weight}): {check.evidence if check.passed else check.missing}")
    lines.extend(["", "## Blockers"])
    if report.blockers:
        lines.extend(f"- {item}" for item in report.blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in report.next_steps)
    return "\n".join(lines)


def _file_check(root: Path, name: str, weight: int, relative_path: str) -> ReadinessCheck:
    path = root / relative_path
    return ReadinessCheck(
        name=name,
        weight=weight,
        passed=path.exists(),
        evidence=relative_path,
        missing=f"missing {relative_path}",
    )


def _all_files_check(root: Path, name: str, weight: int, relative_paths: list[str]) -> ReadinessCheck:
    missing = [relative_path for relative_path in relative_paths if not (root / relative_path).exists()]
    return ReadinessCheck(
        name=name,
        weight=weight,
        passed=not missing,
        evidence=", ".join(relative_paths),
        missing=f"missing {', '.join(missing)}" if missing else "",
    )


def _dir_has_files_check(root: Path, name: str, weight: int, relative_dir: str, pattern: str) -> ReadinessCheck:
    directory = root / relative_dir
    count = len(list(directory.glob(pattern))) if directory.exists() else 0
    return ReadinessCheck(
        name=name,
        weight=weight,
        passed=count > 0,
        evidence=f"{relative_dir}/{pattern}: {count} files",
        missing=f"missing {relative_dir}/{pattern}",
    )


def _band(percent: float) -> str:
    if percent >= 90:
        return "ready_with_evidence"
    if percent >= 80:
        return "application_ready_but_needs_beta_evidence"
    if percent >= 60:
        return "promising_but_incomplete"
    return "not_ready"


def _next_steps(blockers: list[str]) -> list[str]:
    if not blockers:
        return ["Submit application materials and keep improving Stage 3."]
    result = ["Fix blockers before claiming full readiness."]
    if any("BETA_VALIDATION_REPORT_ZH.md" in blocker for blocker in blockers):
        result.append("Run real Feishu beta validation and generate docs/BETA_VALIDATION_REPORT_ZH.md.")
        result.append("Add beta group task-card screenshot or GIF to the report.")
    return result
