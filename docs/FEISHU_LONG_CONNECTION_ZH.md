# 飞书长链接模式

飞书长链接模式不需要公网 HTTPS callback。

本仓库现在支持两种事件接入模式：

- `feishu.event_mode = "callback"`：HTTP `/webhook`，需要公网 HTTPS callback、verification token、可选 encrypt key。
- `feishu.event_mode = "long_connection"`：长链接接收事件，不需要公网 callback；仍需要 beta app、app_id、app_secret、beta 群 allowlist。

## 配置

```toml
[feishu]
send_mode = "live"
event_mode = "long_connection"
app_id = "cli_xxx"
app_secret = "..."
group_chat_id = "oc_xxx"
send_allowlist = ["oc_xxx"]
verification_token = ""
encrypt_key = ""
```

## 本地检查

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url ""
```

长链接模式下，preflight 会把 `long_connection_transport` 作为通过项，不会要求公网 URL。

## 长链接 dry-run

```bash
stock-agent-orchestrator run-long-connection --config configs/beta.live.toml --db .runtime/long-connection.db --dry-run --format markdown
```

dry-run 不连接飞书，只验证：

- 配置是 `long_connection`。
- gateway/worker/state store 可以初始化。
- `/healthz` 等价状态结构可用。
- 不需要公网 callback。

## 当前边界

已完成：

- 配置层支持 `callback` / `long_connection`。
- long_connection preflight 不再要求公网 callback。
- `run-long-connection --dry-run` 已接入现有 gateway/worker/operation 架构。
- final gate 在长链接模式下跳过公网 callback deploy plan。

仍待真实 beta 前完成：

- 安装并确认飞书长链接 SDK，例如 `lark-oapi`。
- 把 SDK 收到的消息事件绑定到 `FeishuLongConnectionRuntime.handle_event_payload()`。
- 在临时 beta 群实测任务卡创建和更新。
- 生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
