import base64
import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.connectors.feishu import FakeFeishuClient
from stock_agent_orchestrator.connectors.feishu_http import (
    build_webhook_server,
    calculate_lark_signature,
    decrypt_lark_payload,
)


class FeishuHTTPTests(unittest.TestCase):
    def test_http_webhook_health_challenge_and_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeFeishuClient()
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=load_config(Path("configs/beta.example.toml")),
                db_path=Path(tmp) / "beta.db",
                feishu_client=client,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                health = self._get_json(f"{base}/healthz")
                self.assertTrue(health["ok"])
                self.assertEqual(health["gateway"]["status"], "connected")
                self.assertEqual(health["gateway"]["accepted_count"], 0)

                challenge = self._post_json(f"{base}/webhook", {"challenge": "abc"})
                self.assertEqual(challenge, {"challenge": "abc"})

                result = self._post_json(f"{base}/webhook", self._message_payload())
                self.assertTrue(result["accepted"])
                self.assertTrue(result["enqueued"])
                self.assertEqual(result["worker_report"]["handled"], 1)
                self.assertEqual(len(client.sent_messages), 1)
                self.assertIn("任务卡：BETA-0001", client.sent_messages[0].text)
                health_after = self._get_json(f"{base}/healthz")
                self.assertEqual(health_after["gateway"]["accepted_count"], 2)
                self.assertEqual(health_after["gateway"]["enqueued_count"], 1)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_rejects_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=load_config(Path("configs/beta.example.toml")),
                db_path=Path(tmp) / "beta.db",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    data=b"{bad",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_rejects_invalid_verification_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            config = replace(config, feishu=replace(config.feishu, verification_token="verify-token"))
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=config,
                db_path=Path(tmp) / "beta.db",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = self._message_payload()
                payload["token"] = "wrong"
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_accepts_valid_lark_signature_when_encrypt_key_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeFeishuClient()
            config = load_config(Path("configs/beta.example.toml"))
            config = replace(config, feishu=replace(config.feishu, encrypt_key="encrypt-key"))
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=config,
                db_path=Path(tmp) / "beta.db",
                feishu_client=client,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = self._message_payload()
                result = self._post_json(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    payload,
                    encrypt_key="encrypt-key",
                )
                self.assertTrue(result["accepted"])
                self.assertTrue(result["enqueued"])
                self.assertEqual(len(client.sent_messages), 1)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_rejects_missing_lark_signature_when_encrypt_key_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            config = replace(config, feishu=replace(config.feishu, encrypt_key="encrypt-key"))
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=config,
                db_path=Path(tmp) / "beta.db",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    data=json.dumps(self._message_payload()).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_rejects_invalid_lark_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path("configs/beta.example.toml"))
            config = replace(config, feishu=replace(config.feishu, encrypt_key="encrypt-key"))
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=config,
                db_path=Path(tmp) / "beta.db",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = json.dumps(self._message_payload()).encode("utf-8")
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Lark-Request-Timestamp": "1780581200",
                        "X-Lark-Request-Nonce": "nonce",
                        "X-Lark-Signature": "bad-signature",
                    },
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_accepts_encrypted_lark_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeFeishuClient()
            config = load_config(Path("configs/beta.example.toml"))
            config = replace(config, feishu=replace(config.feishu, encrypt_key="encrypt-key"))
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=config,
                db_path=Path(tmp) / "beta.db",
                feishu_client=client,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                encrypted_payload = {"encrypt": encrypt_lark_payload(self._message_payload(), "encrypt-key")}
                result = self._post_json(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    encrypted_payload,
                    encrypt_key="encrypt-key",
                )

                self.assertTrue(result["accepted"])
                self.assertTrue(result["enqueued"])
                self.assertEqual(len(client.sent_messages), 1)
                self.assertIn("任务卡：BETA-0001", client.sent_messages[0].text)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_webhook_rejects_encrypted_payload_without_encrypt_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_webhook_server(
                host="127.0.0.1",
                port=0,
                config=load_config(Path("configs/beta.example.toml")),
                db_path=Path(tmp) / "beta.db",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_address[1]}/webhook",
                    data=json.dumps({"encrypt": encrypt_lark_payload(self._message_payload(), "encrypt-key")}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_decrypt_lark_payload_round_trips_json_object(self) -> None:
        encrypted = encrypt_lark_payload({"challenge": "abc"}, "encrypt-key")

        payload = decrypt_lark_payload(encrypted=encrypted, encrypt_key="encrypt-key")

        self.assertEqual(payload, {"challenge": "abc"})

    def _get_json(self, url: str) -> dict:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, url: str, payload: dict, *, encrypt_key: str = "") -> dict:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if encrypt_key:
            timestamp = "1780581200"
            nonce = "nonce"
            headers.update(
                {
                    "X-Lark-Request-Timestamp": timestamp,
                    "X-Lark-Request-Nonce": nonce,
                    "X-Lark-Signature": calculate_lark_signature(
                        timestamp=timestamp,
                        nonce=nonce,
                        encrypt_key=encrypt_key,
                        raw_body=body,
                    ),
                }
            )
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _message_payload(self) -> dict:
        return {
            "event_id": "evt-http-1",
            "event": {
                "sender": {"sender_id": {"open_id": "user-open-id"}},
                "message": {
                    "message_id": "msg-http-1",
                    "chat_id": "replace-me",
                    "content": json.dumps({"text": "@小C-beta 今天先给我一份候选池"}, ensure_ascii=False),
                    "mentions": [{"id": {"open_id": "replace-me"}}],
                },
            },
        }

def encrypt_lark_payload(payload: dict, encrypt_key: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    padding_size = 16 - (len(raw) % 16)
    padded = raw + bytes([padding_size]) * padding_size
    iv = b"0123456789abcdef"
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode("utf-8")


if __name__ == "__main__":
    unittest.main()
