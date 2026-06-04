from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BetaLiveIntakeItem:
    name: str
    env_name: str
    source: str
    example: str
    sensitive: bool
    required: bool
    validation: str
    risk: str


@dataclass(frozen=True, slots=True)
class BetaLiveIntakeChecklist:
    ok: bool
    stage: str
    items: list[BetaLiveIntakeItem]
    operator_steps: list[str]
    commands: list[str]
    stop_conditions: list[str]
    next_steps: list[str]


def build_beta_live_intake_checklist(*, shell: str = "powershell") -> BetaLiveIntakeChecklist:
    normalized = shell.strip().lower()
    if normalized not in {"powershell", "bash"}:
        raise ValueError("shell must be powershell or bash")
    return BetaLiveIntakeChecklist(
        ok=True,
        stage="collect_real_feishu_beta_values",
        items=_items(),
        operator_steps=_operator_steps(),
        commands=_commands(shell=normalized),
        stop_conditions=_stop_conditions(),
        next_steps=_next_steps(),
    )


def beta_live_intake_checklist_to_dict(checklist: BetaLiveIntakeChecklist) -> dict[str, Any]:
    return asdict(checklist)


def beta_live_intake_checklist_to_markdown(checklist: BetaLiveIntakeChecklist) -> str:
    lines = [
        "# 飞书 Beta Live Intake Checklist",
        "",
        f"- ok: `{str(checklist.ok).lower()}`",
        f"- stage: `{checklist.stage}`",
        "",
        "## Required Values",
        "",
        "| name | env | source | sensitive | validation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in checklist.items:
        lines.append(
            f"| {item.name} | `{item.env_name}` | {item.source} | `{str(item.sensitive).lower()}` | {item.validation} |"
        )
    lines.extend(["", "## Operator Steps"])
    lines.extend(f"- {step}" for step in checklist.operator_steps)
    lines.extend(["", "## Commands"])
    for command in checklist.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in checklist.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in checklist.next_steps)
    return "\n".join(lines)


def _items() -> list[BetaLiveIntakeItem]:
    return [
        BetaLiveIntakeItem(
            name="candidate list path",
            env_name="STOCK_AGENT_CANDIDATE_LIST",
            source="本机或共享目录里的候选池 markdown 文件",
            example="C:\\path\\to\\candidate_list.md",
            sensitive=False,
            required=True,
            validation="文件路径应存在或后续可由小巴生成",
            risk="路径填错会导致候选池桥接失败",
        ),
        BetaLiveIntakeItem(
            name="seven layer reports path",
            env_name="STOCK_AGENT_SEVEN_LAYER_REPORTS",
            source="小智七层数据报告目录",
            example="C:\\path\\to\\seven_layer",
            sensitive=False,
            required=True,
            validation="目录路径应存在或后续可创建",
            risk="路径填错会导致单票研究卡无法读取七层数据",
        ),
        BetaLiveIntakeItem(
            name="entry monitor reports path",
            env_name="STOCK_AGENT_ENTRY_MONITOR_REPORTS",
            source="入场监控报告目录",
            example="C:\\path\\to\\entry_monitor",
            sensitive=False,
            required=True,
            validation="目录路径应存在或后续可创建",
            risk="路径填错会影响后续模拟盘和复盘证据",
        ),
        BetaLiveIntakeItem(
            name="sqlite db path",
            env_name="STOCK_AGENT_SQLITE_DB",
            source="本机 runtime 目录",
            example="./runtime/beta-live.db",
            sensitive=False,
            required=True,
            validation="父目录可写",
            risk="路径不可写会导致任务无法落库",
        ),
        BetaLiveIntakeItem(
            name="beta group chat id",
            env_name="FEISHU_GROUP_CHAT_ID",
            source="飞书 beta 群 open_chat_id",
            example="oc_xxx",
            sensitive=False,
            required=True,
            validation="必须加入 send_allowlist",
            risk="填成正式群会打扰现有工作流",
        ),
        BetaLiveIntakeItem(
            name="owner open id",
            env_name="FEISHU_OWNER_OPEN_ID",
            source="小C-beta bot 或 owner open_id",
            example="ou_xiaoc_beta",
            sensitive=False,
            required=True,
            validation="应对应 beta 角色，不要填正式小C",
            risk="角色填错会导致 mention 识别和任务归属错误",
        ),
        BetaLiveIntakeItem(
            name="data open id",
            env_name="FEISHU_DATA_OPEN_ID",
            source="小智-beta open_id",
            example="ou_xiaozhi_beta",
            sensitive=False,
            required=True,
            validation="应对应 beta 角色，不要填正式小智",
            risk="后续七层数据更新无法绑定正确 agent",
        ),
        BetaLiveIntakeItem(
            name="analyst open id",
            env_name="FEISHU_ANALYST_OPEN_ID",
            source="小巴-beta open_id",
            example="ou_xiaoba_beta",
            sensitive=False,
            required=True,
            validation="应对应 beta 角色，不要填正式小巴",
            risk="RSI 分析和复盘更新无法绑定正确 agent",
        ),
        BetaLiveIntakeItem(
            name="Feishu app id",
            env_name="FEISHU_APP_ID",
            source="飞书开放平台应用凭证",
            example="cli_xxx",
            sensitive=False,
            required=True,
            validation="必须属于 beta 验证使用的应用",
            risk="填错应用会导致 token 获取或事件订阅失败",
        ),
        BetaLiveIntakeItem(
            name="Feishu app secret",
            env_name="FEISHU_APP_SECRET",
            source="飞书开放平台应用凭证",
            example="<secret>",
            sensitive=True,
            required=True,
            validation="只写入 ignored config 或环境变量",
            risk="泄露后应立即在飞书开放平台轮换",
        ),
        BetaLiveIntakeItem(
            name="Feishu event mode",
            env_name="FEISHU_EVENT_MODE",
            source="接入方式选择：callback 或 long_connection",
            example="long_connection",
            sensitive=False,
            required=True,
            validation="长链接模式不需要公网 callback；callback 模式需要公网 HTTPS",
            risk="模式选错会导致准入门错误阻断或接错通道",
        ),
        BetaLiveIntakeItem(
            name="verification token",
            env_name="FEISHU_VERIFICATION_TOKEN",
            source="飞书 callback 事件订阅 verification token",
            example="<token>",
            sensitive=True,
            required=False,
            validation="callback 模式必须填写；long_connection 模式可留空",
            risk="callback 模式缺失会拒绝真实飞书 callback",
        ),
        BetaLiveIntakeItem(
            name="encrypt key",
            env_name="FEISHU_ENCRYPT_KEY",
            source="飞书 callback 事件订阅 encrypt key",
            example="<encrypt-key>",
            sensitive=True,
            required=False,
            validation="callback 加密模式必须填写；long_connection 模式可留空",
            risk="callback 加密模式缺失会无法处理加密事件",
        ),
    ]


def _operator_steps() -> list[str]:
    return [
        "先创建临时 beta 群，不使用当前正式工作流群。",
        "确认 beta 群中只有 BOOS、小C-beta、小智-beta、小巴-beta 和必要测试人员。",
        "在飞书开放平台准备 beta 应用，并选择 callback 或 long_connection 事件接入方式。",
        "逐项收集 Required Values，不把 secret 粘贴到公开聊天或仓库。",
        "填完环境变量后生成 ignored 的 configs/beta.live.toml。",
    ]


def _commands(*, shell: str) -> list[str]:
    return [
        f"stock-agent-orchestrator beta-live-env-template --shell {shell}",
        "stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown",
        "stock-agent-orchestrator beta-live-config-status --config configs/beta.live.toml --format markdown",
        "stock-agent-orchestrator run-long-connection --config configs/beta.live.toml --db .runtime/long-connection.db --dry-run --format markdown",
        "stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown",
    ]


def _stop_conditions() -> list[str]:
    return [
        "没有临时 beta 群时停止，不要接入正式群。",
        "任何 open_id 或 chat_id 不确定时停止，先核对。",
        "app_secret 以及 callback 模式下的 verification_token、encrypt_key 泄露到聊天或仓库时停止并轮换。",
        "configs/beta.live.toml 未被 .gitignore 保护时停止。",
        "beta-live-config-status 未通过时停止。",
    ]


def _next_steps() -> list[str]:
    return [
        "按 Required Values 收集真实值。",
        "用 beta-live-env-template 生成填写模板。",
        "用 beta-live-config-from-env 写入 ignored 配置。",
        "长链接模式先通过 run-long-connection --dry-run；callback 模式先通过 callback deploy/probe。",
        "通过 beta-live-readiness-bundle 后再进入真实 beta 群验证。",
    ]
