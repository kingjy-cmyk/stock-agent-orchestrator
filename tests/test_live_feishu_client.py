import json
import unittest
import urllib.request

from stock_agent_orchestrator.config import FeishuConfig
from stock_agent_orchestrator.connectors.feishu import (
    ClientOperationGateway,
    FakeFeishuClient,
    FeishuOperation,
    FeishuOperationError,
    FeishuOperationKind,
    LiveFeishuClient,
    build_feishu_client,
    build_operation_gateway,
)


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class ErrorRecorder:
    def __init__(self) -> None:
        self.errors: list[FeishuOperationError] = []

    def record_operation_error(self, error: FeishuOperationError) -> None:
        self.errors.append(error)


class LiveFeishuClientTests(unittest.TestCase):
    def test_build_client_defaults_to_fake(self) -> None:
        client = build_feishu_client(
            FeishuConfig(
                group_chat_id="chat",
                owner_open_id="owner",
                data_open_id="data",
                analyst_open_id="analyst",
            )
        )

        self.assertIsInstance(client, FakeFeishuClient)

    def test_live_client_requires_explicit_allow(self) -> None:
        config = FeishuConfig(
            group_chat_id="chat",
            owner_open_id="owner",
            data_open_id="data",
            analyst_open_id="analyst",
            app_id="app",
            app_secret="secret",
            send_mode="live",
        )

        with self.assertRaises(RuntimeError):
            build_feishu_client(config)

    def test_live_client_fetches_token_and_sends_message(self) -> None:
        requests: list[urllib.request.Request] = []

        def opener(request: urllib.request.Request):
            requests.append(request)
            if request.full_url.endswith("/open-apis/auth/v3/tenant_access_token/internal"):
                return FakeHTTPResponse({"code": 0, "tenant_access_token": "token-1"})
            return FakeHTTPResponse({"code": 0, "data": {"message_id": "msg-live-1"}})

        client = LiveFeishuClient(app_id="app", app_secret="secret", opener=opener)

        sent = client.send_message("chat-id", "hello")

        self.assertEqual(sent.message_id, "msg-live-1")
        self.assertEqual(sent.metadata["client"], "live")
        self.assertEqual(len(requests), 2)
        self.assertIn("tenant_access_token", requests[0].full_url)
        self.assertIn("receive_id_type=chat_id", requests[1].full_url)
        self.assertEqual(requests[1].headers["Authorization"], "Bearer token-1")

    def test_live_client_sends_updateable_interactive_card(self) -> None:
        requests: list[urllib.request.Request] = []

        def opener(request: urllib.request.Request):
            requests.append(request)
            if request.full_url.endswith("/open-apis/auth/v3/tenant_access_token/internal"):
                return FakeHTTPResponse({"code": 0, "tenant_access_token": "token-1"})
            return FakeHTTPResponse({"code": 0, "data": {"message_id": "msg-card-1"}})

        client = LiveFeishuClient(app_id="app", app_secret="secret", opener=opener)

        sent = client.send_card("chat-id", "## 任务卡：BETA-0001")

        body = json.loads(requests[1].data.decode("utf-8"))  # type: ignore[union-attr]
        content = json.loads(body["content"])
        self.assertEqual(sent.message_id, "msg-card-1")
        self.assertEqual(body["msg_type"], "interactive")
        self.assertTrue(content["config"]["update_multi"])
        self.assertIn("任务卡：BETA-0001", content["elements"][0]["content"])

    def test_live_client_updates_interactive_card_by_message_id(self) -> None:
        requests: list[urllib.request.Request] = []

        def opener(request: urllib.request.Request):
            requests.append(request)
            if request.full_url.endswith("/open-apis/auth/v3/tenant_access_token/internal"):
                return FakeHTTPResponse({"code": 0, "tenant_access_token": "token-1"})
            return FakeHTTPResponse({"code": 0, "data": {}})

        client = LiveFeishuClient(app_id="app", app_secret="secret", opener=opener)

        sent = client.update_card("om_card_1", "## 任务卡：BETA-0001\n- 状态：筛选中")

        body = json.loads(requests[1].data.decode("utf-8"))  # type: ignore[union-attr]
        content = json.loads(body["content"])
        self.assertEqual(sent.message_id, "om_card_1")
        self.assertEqual(requests[1].get_method(), "PATCH")
        self.assertIn("/open-apis/im/v1/messages/om_card_1", requests[1].full_url)
        self.assertTrue(content["config"]["update_multi"])
        self.assertIn("筛选中", content["elements"][0]["content"])

    def test_operation_gateway_applies_send_card(self) -> None:
        client = FakeFeishuClient()
        gateway = ClientOperationGateway(client)
        operation = FeishuOperation(
            kind=FeishuOperationKind.SEND_CARD,
            chat_id="chat",
            text="task card",
        )

        sent = gateway.apply([operation])

        self.assertEqual(len(sent), 1)
        self.assertEqual(operation.message_id, "fake-msg-0001")
        self.assertEqual(client.sent_messages[0].text, "task card")

    def test_operation_gateway_applies_update_card(self) -> None:
        client = FakeFeishuClient()
        gateway = ClientOperationGateway(client)
        created = gateway.apply(
            [
                FeishuOperation(
                    kind=FeishuOperationKind.SEND_CARD,
                    chat_id="chat",
                    text="task card",
                )
            ]
        )[0]
        operation = FeishuOperation(
            kind=FeishuOperationKind.UPDATE_CARD,
            chat_id="chat",
            message_id=created.message_id,
            text="updated task card",
        )

        sent = gateway.apply([operation])

        self.assertEqual(len(sent), 1)
        self.assertEqual(operation.message_id, "fake-msg-0001")
        self.assertEqual(len(client.sent_messages), 1)
        self.assertEqual(len(client.updated_messages), 1)
        self.assertEqual(client.sent_messages[0].text, "updated task card")

    def test_operation_gateway_rejects_chat_outside_allowlist_and_records_error(self) -> None:
        recorder = ErrorRecorder()
        gateway = build_operation_gateway(
            FeishuConfig(
                group_chat_id="allowed-chat",
                owner_open_id="owner",
                data_open_id="data",
                analyst_open_id="analyst",
                send_allowlist=["allowed-chat"],
            ),
            error_recorder=recorder,
        )

        with self.assertRaises(RuntimeError):
            gateway.apply(
                [
                    FeishuOperation(
                        kind=FeishuOperationKind.SEND_CARD,
                        chat_id="other-chat",
                        text="task card",
                        metadata={"task_id": "BETA-0001"},
                    )
                ]
            )

        self.assertEqual(len(recorder.errors), 1)
        self.assertEqual(recorder.errors[0].task_id, "BETA-0001")
        self.assertIn("allowlist", recorder.errors[0].message)


if __name__ == "__main__":
    unittest.main()
