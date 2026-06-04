from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str
    environment: str
    mode: str


@dataclass(frozen=True, slots=True)
class RoleConfig:
    owner: str
    data: str
    analyst: str


@dataclass(frozen=True, slots=True)
class AutomationConfig:
    auto_advance_within_rules: bool
    allow_real_trading: bool
    require_user_review_for_new_rules: bool


@dataclass(frozen=True, slots=True)
class PathConfig:
    candidate_list: str
    seven_layer_reports: str
    entry_monitor_reports: str
    sqlite_db: str


@dataclass(frozen=True, slots=True)
class FeishuConfig:
    group_chat_id: str
    owner_open_id: str
    data_open_id: str
    analyst_open_id: str
    app_id: str = ""
    app_secret: str = ""
    api_base_url: str = "https://open.feishu.cn"
    send_mode: str = "fake"
    send_allowlist: list[str] = field(default_factory=list)
    verification_token: str = ""
    encrypt_key: str = ""


@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
    project: ProjectConfig
    roles: RoleConfig
    automation: AutomationConfig
    paths: PathConfig
    feishu: FeishuConfig


@dataclass(frozen=True, slots=True)
class ConfigValidationIssue:
    severity: str
    field: str
    message: str


REQUIRED_SECTIONS = ("project", "roles", "automation", "paths", "feishu")
PLACEHOLDER_VALUES = {
    "",
    "replace-me",
    "/path/to/candidate_list.md",
    "/path/to/seven_layer_reports",
    "/path/to/entry_monitor_reports",
}


def load_config(path: Path) -> OrchestratorConfig:
    payload = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    missing = [section for section in REQUIRED_SECTIONS if section not in payload]
    if missing:
        raise ValueError(f"missing config sections: {', '.join(missing)}")
    return OrchestratorConfig(
        project=ProjectConfig(**payload["project"]),
        roles=RoleConfig(**payload["roles"]),
        automation=AutomationConfig(**payload["automation"]),
        paths=PathConfig(**payload["paths"]),
        feishu=FeishuConfig(**payload["feishu"]),
    )


def validate_config(config: OrchestratorConfig) -> list[ConfigValidationIssue]:
    issues: list[ConfigValidationIssue] = []
    if config.project.environment not in {"beta", "formal", "local"}:
        issues.append(ConfigValidationIssue("error", "project.environment", "must be beta, formal, or local"))
    if config.project.mode not in {"preflight", "shadow", "active"}:
        issues.append(ConfigValidationIssue("error", "project.mode", "must be preflight, shadow, or active"))
    if config.project.environment == "formal" and config.project.mode == "active":
        issues.append(ConfigValidationIssue("error", "project.mode", "formal active mode is not allowed by default"))
    if config.automation.allow_real_trading:
        issues.append(ConfigValidationIssue("error", "automation.allow_real_trading", "real trading must stay disabled in MVP"))
    if not config.automation.require_user_review_for_new_rules:
        issues.append(
            ConfigValidationIssue("error", "automation.require_user_review_for_new_rules", "new rules must require user review")
        )
    if config.feishu.send_mode not in {"fake", "live"}:
        issues.append(ConfigValidationIssue("error", "feishu.send_mode", "must be fake or live"))
    if config.feishu.send_mode == "live":
        if config.project.environment != "beta":
            issues.append(ConfigValidationIssue("error", "feishu.send_mode", "live send is only allowed for beta"))
        if config.project.mode != "active":
            issues.append(ConfigValidationIssue("error", "project.mode", "live send requires beta active mode"))
        if (
            not config.feishu.app_id.strip()
            or not config.feishu.app_secret.strip()
            or config.feishu.app_id.strip() in PLACEHOLDER_VALUES
            or config.feishu.app_secret.strip() in PLACEHOLDER_VALUES
        ):
            issues.append(ConfigValidationIssue("error", "feishu.app_id", "live send requires app_id and app_secret"))
        if config.feishu.group_chat_id.strip() not in {value.strip() for value in config.feishu.send_allowlist}:
            issues.append(ConfigValidationIssue("error", "feishu.send_allowlist", "live send requires group_chat_id in send_allowlist"))
        if not config.feishu.verification_token.strip() or config.feishu.verification_token.strip() in PLACEHOLDER_VALUES:
            issues.append(ConfigValidationIssue("error", "feishu.verification_token", "live callback requires verification_token"))

    fields = flatten_config(config)
    for field, value in fields.items():
        if isinstance(value, str) and value.strip() in PLACEHOLDER_VALUES:
            issues.append(ConfigValidationIssue("warning", field, "placeholder value must be replaced before Feishu beta"))
    return issues


def config_to_dict(config: OrchestratorConfig) -> dict[str, Any]:
    return asdict(config)


def validation_to_dict(issues: list[ConfigValidationIssue]) -> list[dict[str, str]]:
    return [asdict(issue) for issue in issues]


def flatten_config(config: OrchestratorConfig) -> dict[str, Any]:
    nested = config_to_dict(config)
    result: dict[str, Any] = {}
    for section, values in nested.items():
        for key, value in values.items():
            result[f"{section}.{key}"] = value
    return result
