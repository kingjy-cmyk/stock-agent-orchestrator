from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import OrchestratorConfig, load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient, FeishuClient, build_operation_gateway
from stock_agent_orchestrator.connectors.feishu_webhook import FeishuWebhookGateway, WebhookResult
from stock_agent_orchestrator.persistence.gateway_state_store import SQLiteGatewayStateStore
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue


@dataclass(frozen=True, slots=True)
class LongConnectionRuntimeStatus:
    ok: bool
    event_mode: str
    sdk_available: bool
    config_path: str
    db_path: str
    state: dict[str, Any]
    next_steps: list[str]


class FeishuLongConnectionRuntime:
    """Long-connection ingress wrapper that reuses the existing gateway stack."""

    def __init__(self, *, config: OrchestratorConfig, db_path: Path, feishu_client: FeishuClient | None = None, allow_live_send: bool = False) -> None:
        self.config = config
        self.db_path = db_path
        self.gateway = FeishuWebhookGateway(
            verification_token="",
            state_store=SQLiteGatewayStateStore(db_path),
            rate_limit_per_minute=config.feishu.webhook_rate_limit_per_minute,
        )
        operation_gateway = (
            None
            if feishu_client
            else build_operation_gateway(config.feishu, allow_live_send=allow_live_send, error_recorder=self.gateway)
        )
        worker = ConnectorWorker(
            queue=BoundedIngressQueue(max_per_instance=1024),
            orchestrator=BetaOrchestratorService(
                config=config,
                store=SQLiteTaskStore(db_path),
                feishu_client=feishu_client,
                operation_gateway=operation_gateway,
            ),
        )
        self.gateway.attach_worker(worker)

    def handle_event_payload(self, payload: dict[str, Any], *, drain: bool = True) -> WebhookResult:
        return self.gateway.handle_payload(payload, drain=drain)

    def state_dict(self) -> dict[str, Any]:
        return self.gateway.state_dict()

    def start(self) -> None:
        if not long_connection_sdk_available():
            raise RuntimeError("Feishu long connection SDK is not installed; install lark-oapi before running live long_connection ingress")
        raise RuntimeError("Feishu long connection SDK adapter wiring is not implemented yet; use --dry-run or finish SDK event binding first")


def build_long_connection_runtime_from_config(
    *,
    config_path: Path,
    db_path: Path,
    allow_live_send: bool = False,
    feishu_client: FeishuClient | None = None,
) -> FeishuLongConnectionRuntime:
    config = load_config(config_path)
    if config.feishu.event_mode != "long_connection":
        raise RuntimeError("run-long-connection requires feishu.event_mode = long_connection")
    return FeishuLongConnectionRuntime(
        config=config,
        db_path=db_path,
        feishu_client=feishu_client,
        allow_live_send=allow_live_send,
    )


def build_long_connection_runtime_status(*, config_path: Path, db_path: Path) -> LongConnectionRuntimeStatus:
    config = load_config(config_path)
    runtime = FeishuLongConnectionRuntime(config=config, db_path=db_path, feishu_client=FakeFeishuClient(), allow_live_send=False)
    sdk_available = long_connection_sdk_available()
    return LongConnectionRuntimeStatus(
        ok=config.feishu.event_mode == "long_connection",
        event_mode=config.feishu.event_mode,
        sdk_available=sdk_available,
        config_path=str(config_path),
        db_path=str(db_path),
        state=runtime.state_dict(),
        next_steps=_next_steps(sdk_available=sdk_available),
    )


def long_connection_runtime_status_to_dict(status: LongConnectionRuntimeStatus) -> dict[str, Any]:
    return asdict(status)


def long_connection_runtime_status_to_markdown(status: LongConnectionRuntimeStatus) -> str:
    lines = [
        "# Feishu Long Connection Runtime",
        "",
        f"- ok: `{str(status.ok).lower()}`",
        f"- event_mode: `{status.event_mode}`",
        f"- sdk_available: `{str(status.sdk_available).lower()}`",
        f"- config_path: `{status.config_path}`",
        f"- db_path: `{status.db_path}`",
        "",
        "## State",
    ]
    for key, value in status.state.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in status.next_steps)
    return "\n".join(lines)


def long_connection_sdk_available() -> bool:
    try:
        __import__("lark_oapi")
    except Exception:
        return False
    return True


def _next_steps(*, sdk_available: bool) -> list[str]:
    if sdk_available:
        return [
            "Finish SDK event binding and start run-long-connection without --dry-run.",
            "Send one beta group message and collect evidence.",
        ]
    return [
        "Install Feishu long connection SDK package lark-oapi.",
        "Run run-long-connection --dry-run again.",
        "No public callback URL is required for long_connection mode.",
    ]
