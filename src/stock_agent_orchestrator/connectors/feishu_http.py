from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from stock_agent_orchestrator.config import OrchestratorConfig, load_config
from stock_agent_orchestrator.connectors.feishu import FeishuClient, build_operation_gateway
from stock_agent_orchestrator.connectors.feishu_webhook import FeishuWebhookGateway, WebhookResult
from stock_agent_orchestrator.persistence.gateway_state_store import SQLiteGatewayStateStore
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService
from stock_agent_orchestrator.services.connector_worker import ConnectorWorker
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue


class FeishuWebhookHTTPHandler(BaseHTTPRequestHandler):
    gateway: FeishuWebhookGateway
    drain: bool = True
    encrypt_key: str = ""

    def do_GET(self) -> None:
        if self.path != "/healthz":
            self._write_json(404, {"ok": False, "error": "not_found"})
            return
        self._write_json(200, {"ok": True, "gateway": self.gateway.state_dict()})

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self._write_json(404, {"ok": False, "error": "not_found"})
            return
        try:
            raw_body = self._read_body()
        except ValueError as exc:
            self._write_json(400, {"ok": False, "error": str(exc)})
            return
        if not self._signature_is_valid(raw_body):
            self._write_json(403, {"accepted": False, "enqueued": False, "reason": "invalid_lark_signature"})
            return
        try:
            payload = self._decode_json(raw_body)
        except ValueError as exc:
            self._write_json(400, {"ok": False, "error": str(exc)})
            return

        result = self.gateway.handle_payload(payload, drain=self.drain)
        if result.challenge:
            self._write_json(200, {"challenge": result.challenge})
            return
        if result.reason == "invalid_verification_token":
            self._write_json(403, webhook_result_to_dict(result))
            return
        if not result.accepted:
            self._write_json(202, webhook_result_to_dict(result))
            return
        self._write_json(200, webhook_result_to_dict(result))

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid content length") from exc
        return self.rfile.read(length)

    def _decode_json(self, raw: bytes) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid json") from exc
        if not isinstance(payload, dict):
            raise ValueError("json body must be an object")
        return payload

    def _signature_is_valid(self, raw_body: bytes) -> bool:
        encrypt_key = self.encrypt_key.strip()
        if not encrypt_key:
            return True
        timestamp = self.headers.get("X-Lark-Request-Timestamp", "")
        nonce = self.headers.get("X-Lark-Request-Nonce", "")
        signature = self.headers.get("X-Lark-Signature", "")
        if not timestamp or not nonce or not signature:
            return False
        expected = calculate_lark_signature(
            timestamp=timestamp,
            nonce=nonce,
            encrypt_key=encrypt_key,
            raw_body=raw_body,
        )
        return hmac.compare_digest(expected, signature)

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_webhook_server(
    *,
    host: str,
    port: int,
    config: OrchestratorConfig,
    db_path: Path,
    feishu_client: FeishuClient | None = None,
    allow_live_send: bool = False,
    max_per_instance: int = 1024,
    persist_gateway_state: bool = True,
) -> ThreadingHTTPServer:
    gateway = FeishuWebhookGateway(
        verification_token=config.feishu.verification_token,
        state_store=SQLiteGatewayStateStore(db_path) if persist_gateway_state else None,
    )
    operation_gateway = (
        None
        if feishu_client
        else build_operation_gateway(config.feishu, allow_live_send=allow_live_send, error_recorder=gateway)
    )
    worker = ConnectorWorker(
        queue=BoundedIngressQueue(max_per_instance=max_per_instance),
        orchestrator=BetaOrchestratorService(
            config=config,
            store=SQLiteTaskStore(db_path),
            feishu_client=feishu_client,
            operation_gateway=operation_gateway,
        ),
    )
    gateway.attach_worker(worker)

    class Handler(FeishuWebhookHTTPHandler):
        pass

    Handler.gateway = gateway
    Handler.encrypt_key = config.feishu.encrypt_key
    return ThreadingHTTPServer((host, port), Handler)


def build_webhook_server_from_config(
    *,
    host: str,
    port: int,
    config_path: Path,
    db_path: Path,
    allow_live_send: bool = False,
    max_per_instance: int = 1024,
) -> ThreadingHTTPServer:
    return build_webhook_server(
        host=host,
        port=port,
        config=load_config(config_path),
        db_path=db_path,
        allow_live_send=allow_live_send,
        max_per_instance=max_per_instance,
    )


def webhook_result_to_dict(result: WebhookResult) -> dict[str, Any]:
    return {
        "accepted": result.accepted,
        "enqueued": result.enqueued,
        "challenge": result.challenge,
        "reason": result.reason,
        "worker_report": asdict(result.worker_report) if result.worker_report else None,
    }


def calculate_lark_signature(*, timestamp: str, nonce: str, encrypt_key: str, raw_body: bytes) -> str:
    payload = (timestamp + nonce + encrypt_key).encode("utf-8") + raw_body
    return hashlib.sha256(payload).hexdigest()
