from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class BetaCallbackDeployPlan:
    ok: bool
    stage: str
    callback_url: str
    webhook_url: str
    healthz_url: str
    listen_url: str
    public_https: bool
    host: str
    port: int
    config_path: str
    db_path: str
    checks: list[dict[str, str]]
    topology: list[str]
    commands: list[str]
    feishu_console_steps: list[str]
    evidence_to_collect: list[str]
    stop_conditions: list[str]
    next_steps: list[str]


def build_beta_callback_deploy_plan(
    *,
    callback_url: str,
    config_path: str = "configs/beta.live.toml",
    db_path: str = ".runtime/webhook.db",
    host: str = "127.0.0.1",
    port: int = 8787,
) -> BetaCallbackDeployPlan:
    normalized_callback = callback_url.strip().rstrip("/")
    webhook_url = f"{normalized_callback}/webhook" if normalized_callback else ""
    healthz_url = f"{normalized_callback}/healthz" if normalized_callback else ""
    listen_url = f"http://{host}:{port}"
    public_https = _is_public_https(normalized_callback)
    checks = _checks(callback_url=normalized_callback, public_https=public_https, host=host, port=port)
    ok = all(item["status"] == "pass" for item in checks)
    stage = "ready_to_start_callback_probe" if ok else "fix_callback_deploy_plan"
    return BetaCallbackDeployPlan(
        ok=ok,
        stage=stage,
        callback_url=normalized_callback,
        webhook_url=webhook_url,
        healthz_url=healthz_url,
        listen_url=listen_url,
        public_https=public_https,
        host=host,
        port=port,
        config_path=config_path,
        db_path=db_path,
        checks=checks,
        topology=_topology(listen_url=listen_url, callback_url=normalized_callback),
        commands=_commands(
            ok=ok,
            config_path=config_path,
            db_path=db_path,
            host=host,
            port=port,
            callback_url=normalized_callback,
        ),
        feishu_console_steps=_feishu_console_steps(webhook_url=webhook_url),
        evidence_to_collect=_evidence_to_collect(),
        stop_conditions=_stop_conditions(),
        next_steps=_next_steps(ok=ok),
    )


def beta_callback_deploy_plan_to_dict(plan: BetaCallbackDeployPlan) -> dict[str, Any]:
    return asdict(plan)


def beta_callback_deploy_plan_to_markdown(plan: BetaCallbackDeployPlan) -> str:
    lines = [
        "# 飞书 Beta Callback Deploy Plan",
        "",
        f"- ok: `{str(plan.ok).lower()}`",
        f"- stage: `{plan.stage}`",
        f"- listen_url: `{plan.listen_url}`",
        f"- callback_url: `{plan.callback_url or '<missing>'}`",
        f"- webhook_url: `{plan.webhook_url or '<missing>'}`",
        f"- healthz_url: `{plan.healthz_url or '<missing>'}`",
        f"- public_https: `{str(plan.public_https).lower()}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{item['status']}` {item['name']}: {item['message']}" for item in plan.checks)
    lines.extend(["", "## Topology"])
    lines.extend(f"- {item}" for item in plan.topology)
    lines.extend(["", "## Commands"])
    for command in plan.commands:
        lines.extend(["", "```bash", command, "```"])
    lines.extend(["", "## Feishu Console Steps"])
    lines.extend(f"- {item}" for item in plan.feishu_console_steps)
    lines.extend(["", "## Evidence To Collect"])
    lines.extend(f"- {item}" for item in plan.evidence_to_collect)
    lines.extend(["", "## Stop Conditions"])
    lines.extend(f"- {item}" for item in plan.stop_conditions)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in plan.next_steps)
    return "\n".join(lines)


def _is_public_https(callback_url: str) -> bool:
    if not callback_url:
        return False
    parsed = urlparse(callback_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return host not in {"localhost", "127.0.0.1", "::1"} and not host.endswith(".local")


def _checks(*, callback_url: str, public_https: bool, host: str, port: int) -> list[dict[str, str]]:
    return [
        _check("callback_url_present", bool(callback_url), "callback URL is present", "callback URL is missing"),
        _check("callback_url_public_https", public_https, "callback URL is public https", "callback URL must be public https"),
        _check("host_present", bool(host.strip()), "local host is present", "local host is missing"),
        _check("port_valid", 0 < int(port) < 65536, "local port is valid", "local port must be between 1 and 65535"),
    ]


def _check(name: str, ok: bool, pass_message: str, fail_message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "message": pass_message if ok else fail_message}


def _topology(*, listen_url: str, callback_url: str) -> list[str]:
    return [
        f"Local webhook listens on `{listen_url}`.",
        f"Public HTTPS endpoint points to `{callback_url or '<missing>'}`.",
        "Feishu event subscription must point to the public `/webhook` URL, not the local listen URL.",
        "The public tunnel or reverse proxy must forward `/webhook` and `/healthz` to the same local service.",
    ]


def _commands(*, ok: bool, config_path: str, db_path: str, host: str, port: int, callback_url: str) -> list[str]:
    if not ok:
        return [
            "stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown",
            "stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --format markdown",
        ]
    return [
        f"stock-agent-orchestrator run-webhook --config {config_path} --db {db_path} --host {host} --port {port} --allow-live-send",
        f"stock-agent-orchestrator beta-callback-probe --config {config_path} --callback-url {callback_url} --format markdown",
        f"stock-agent-orchestrator collect-beta-evidence --config {config_path} --callback-url {callback_url} --db {db_path} --healthz-json .runtime/healthz.json --report-output docs/BETA_VALIDATION_REPORT_ZH.md --commit <commit>",
    ]


def _feishu_console_steps(*, webhook_url: str) -> list[str]:
    return [
        "Open Feishu Developer Console for the beta app.",
        f"Set event subscription callback URL to `{webhook_url or '<missing>'}`.",
        "Enable message receive event `im.message.receive_v1`.",
        "Confirm verification token and encrypt key match configs/beta.live.toml.",
        "Save the console page screenshot after callback verification succeeds.",
    ]


def _evidence_to_collect() -> list[str]:
    return [
        "Screenshot of public callback URL configured in Feishu Developer Console.",
        "Output of beta-callback-probe showing healthz and challenge pass.",
        ".runtime/healthz.json after real beta message flow.",
        "Beta group task-card screenshot or GIF.",
    ]


def _stop_conditions() -> list[str]:
    return [
        "callback_url is not public https.",
        "Feishu console callback points to localhost or http.",
        "beta-callback-probe fails.",
        "run-webhook is not the same config/db pair used by collect-beta-evidence.",
        "Any operation_error_count appears in /healthz.",
    ]


def _next_steps(*, ok: bool) -> list[str]:
    if ok:
        return [
            "Start run-webhook with the generated command.",
            "Expose the local service through the planned public HTTPS endpoint.",
            "Run beta-callback-probe before configuring or using the beta group.",
        ]
    return [
        "Fix callback URL, host, or port before starting live webhook.",
        "Re-run beta-callback-deploy-plan.",
    ]
