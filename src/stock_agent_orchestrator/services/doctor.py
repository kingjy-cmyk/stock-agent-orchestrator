from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(slots=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


@dataclass(slots=True)
class DoctorReport:
    ok: bool
    checks: list[DoctorCheck]


def run_doctor(runtime_dir: Path = Path(".runtime")) -> DoctorReport:
    runtime_ok = True
    runtime_detail = str(runtime_dir.resolve())
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        probe = runtime_dir / ".doctor-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        runtime_ok = False
        runtime_detail = f"{runtime_detail} ({exc})"

    import_ok = True
    import_detail = "stock_agent_orchestrator importable"
    try:
        import stock_agent_orchestrator  # noqa: F401
    except ImportError as exc:
        import_ok = False
        import_detail = str(exc)

    checks = [
        DoctorCheck(
            "python",
            sys.version_info >= (3, 11),
            f"{platform.python_version()} ({sys.executable})",
        ),
        DoctorCheck("runtime_dir", runtime_ok, runtime_detail),
        DoctorCheck("package_import", import_ok, import_detail),
    ]
    return DoctorReport(ok=all(check.ok for check in checks), checks=checks)


def doctor_report_to_dict(report: DoctorReport) -> dict:
    return {"ok": report.ok, "checks": [asdict(check) for check in report.checks]}
