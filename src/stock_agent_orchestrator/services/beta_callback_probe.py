from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable

from stock_agent_orchestrator.config import OrchestratorConfig
from stock_agent_orchestrator.connectors.feishu_http import calculate_lark_signature


@dataclass(frozen=True, slots=True)
class CallbackProbeCheck:
    name: str
    status: str
    message: str
    status_code: int = 0


@dataclass(frozen=True, slots=True)
class CallbackProbeReport:
    ok: bool
    callback_url: str
    healthz_url: str
    webhook_url: str
    checks: list[CallbackProbeCheck]
    healthz: dict[str, Any]
    challenge_response: dict[str, Any]
    next_steps: list[str]


def run_beta_callback_probe(
    *,
    config: OrchestratorConfig,
    callback_url: str,
    challenge: str = "stock-agent-orchestrator-probe",
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> CallbackProbeReport:
    opener = opener or urllib.request.urlopen
    base_url = callback_url.strip().rstrip("/")
    healthz_url = f"{base_url}/healthz" if base_url else ""
    webhook_url = f"{base_url}/webhook" if base_url else ""
    checks: list[CallbackProbeCheck] = []

    healthz, healthz_check = _get_json(healthz_url, opener=opener)
    checks.append(healthz_check)

    challenge_payload = {"challenge": challenge}
    if config.feishu.verification_token.strip():
        challenge_payload["token"] = config.feishu.verification_token.strip()
    challenge_response, challenge_check = _post_json(
        webhook_url,
        challenge_payload,
        encrypt_key=config.feishu.encrypt_key,
        opener=opener,
    )
    checks.append(challenge_check)

    if healthz:
        gateway = healthz.get("gateway") if isinstance(healthz.get("gateway"), dict) else {}
        checks.append(
            CallbackProbeCheck(
                name="healthz_gateway_status",
                status="pass" if str(gateway.get("status") or "") == "connected" else "fail",
                message=f"gateway status is {gateway.get('status') or '<missing>'}",
            )
        )
    if challenge_response:
        checks.append(
            CallbackProbeCheck(
                name="challenge_echo",
                status="pass" if challenge_response.get("challenge") == challenge else "fail",
                message="webhook challenge echoed" if challenge_response.get("challenge") == challenge else "webhook challenge not echoed",
            )
        )

    ok = all(check.status == "pass" for check in checks)
    return CallbackProbeReport(
        ok=ok,
        callback_url=base_url,
        healthz_url=healthz_url,
        webhook_url=webhook_url,
        checks=checks,
        healthz=healthz,
        challenge_response=challenge_response,
        next_steps=_next_steps(ok),
    )


def callback_probe_report_to_dict(report: CallbackProbeReport) -> dict[str, Any]:
    return asdict(report)


def callback_probe_report_to_markdown(report: CallbackProbeReport) -> str:
    lines = [
        "# Feishu Beta Callback Probe",
        "",
        f"- ok: `{str(report.ok).lower()}`",
        f"- callback_url: `{report.callback_url or '<missing>'}`",
        f"- healthz_url: `{report.healthz_url or '<missing>'}`",
        f"- webhook_url: `{report.webhook_url or '<missing>'}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- `{check.status}` {check.name}: {check.message}" for check in report.checks)
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {step}" for step in report.next_steps)
    return "\n".join(lines)


def _get_json(url: str, *, opener: Callable[[urllib.request.Request], Any]) -> tuple[dict[str, Any], CallbackProbeCheck]:
    if not url:
        return {}, CallbackProbeCheck("healthz_reachable", "fail", "callback URL is required")
    request = urllib.request.Request(url, method="GET")
    return _request_json(request, "healthz_reachable", opener=opener)


def _post_json(
    url: str,
    payload: dict[str, str],
    *,
    encrypt_key: str,
    opener: Callable[[urllib.request.Request], Any],
) -> tuple[dict[str, Any], CallbackProbeCheck]:
    if not url:
        return {}, CallbackProbeCheck("webhook_challenge", "fail", "callback URL is required")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if encrypt_key.strip():
        timestamp = "1780581200"
        nonce = "stock-agent-orchestrator-probe"
        headers.update(
            {
                "X-Lark-Request-Timestamp": timestamp,
                "X-Lark-Request-Nonce": nonce,
                "X-Lark-Signature": calculate_lark_signature(
                    timestamp=timestamp,
                    nonce=nonce,
                    encrypt_key=encrypt_key.strip(),
                    raw_body=body,
                ),
            }
        )
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return _request_json(request, "webhook_challenge", opener=opener)


def _request_json(
    request: urllib.request.Request,
    name: str,
    *,
    opener: Callable[[urllib.request.Request], Any],
) -> tuple[dict[str, Any], CallbackProbeCheck]:
    try:
        with opener(request) as response:
            status_code = int(getattr(response, "status", 200))
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {}, CallbackProbeCheck(name, "fail", f"http error {exc.code}", status_code=exc.code)
    except Exception as exc:
        return {}, CallbackProbeCheck(name, "fail", str(exc))
    if not isinstance(payload, dict):
        return {}, CallbackProbeCheck(name, "fail", "response json must be an object", status_code=status_code)
    return payload, CallbackProbeCheck(name, "pass" if 200 <= status_code < 300 else "fail", f"http {status_code}", status_code=status_code)


def _next_steps(ok: bool) -> list[str]:
    if ok:
        return [
            "Configure Feishu event subscription callback to the probed webhook URL.",
            "Send one beta group @小C-beta delegation.",
            "Save /healthz JSON and generate docs/BETA_VALIDATION_REPORT_ZH.md.",
        ]
    return [
        "Fix public callback reachability before configuring Feishu event subscription.",
        "Confirm run-webhook is running behind the same public callback URL.",
        "Run beta-callback-probe again.",
    ]
