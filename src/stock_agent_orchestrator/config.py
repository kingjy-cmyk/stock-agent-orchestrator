from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
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
PLACEHOLDER_VALUES = {"", "replace-me", "/path/to/candidate_list.md", "/path/to/seven_layer_reports", "/path/to/entry_monitor_reports"}


def load_config(path: Path) -> OrchestratorConfig:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
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
