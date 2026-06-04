from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BetaLiveConfigInitResult:
    created: bool
    output_path: str
    template_path: str
    force: bool
    next_steps: list[str]
    warnings: list[str]


def init_beta_live_config(*, template_path: Path, output_path: Path, force: bool = False) -> BetaLiveConfigInitResult:
    if not template_path.exists():
        raise FileNotFoundError(f"template not found: {template_path}")
    if output_path.exists() and not force:
        return BetaLiveConfigInitResult(
            created=False,
            output_path=str(output_path),
            template_path=str(template_path),
            force=force,
            next_steps=[
                "Review the existing config instead of overwriting it.",
                f"Run: stock-agent-orchestrator beta-live-config-status --config {output_path} --format markdown",
            ],
            warnings=[
                "Output config already exists; no changes were made.",
                "Use --force only if you intentionally want to recreate the local beta config.",
            ],
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
    return BetaLiveConfigInitResult(
        created=True,
        output_path=str(output_path),
        template_path=str(template_path),
        force=force,
        next_steps=[
            "Replace all placeholder values in the generated config.",
            f"Run: stock-agent-orchestrator beta-live-config-status --config {output_path} --format markdown",
            f"Run: stock-agent-orchestrator beta-validation-guide --config {output_path} --callback-url https://your-public-domain.example --format markdown",
        ],
        warnings=[
            "Do not commit configs/beta.live.toml; it contains app_secret, verification_token, and encrypt_key.",
            "configs/beta.live.toml is ignored by .gitignore in this repository.",
        ],
    )


def beta_live_config_init_to_dict(result: BetaLiveConfigInitResult) -> dict:
    return asdict(result)


def beta_live_config_init_to_markdown(result: BetaLiveConfigInitResult) -> str:
    lines = [
        "# Beta Live Config Init",
        "",
        f"- created: `{str(result.created).lower()}`",
        f"- output_path: `{result.output_path}`",
        f"- template_path: `{result.template_path}`",
        f"- force: `{str(result.force).lower()}`",
        "",
        "## Next Steps",
    ]
    lines.extend(f"- {step}" for step in result.next_steps)
    if result.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)
