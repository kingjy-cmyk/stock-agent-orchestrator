# 飞书连接器架构

## 参考来源

本项目的飞书连接器设计参考当前 Codex 飞书通道的二进程模式，但不照搬实现。

Codex 飞书通道里的关键模式是：

- `Gateway` 只负责平台接入：启动、接收飞书事件、发送 operations。
- `Daemon / Worker` 负责业务处理：状态、任务、运行时、恢复。
- 中间用 ingress queue 隔离入口和业务处理。
- 入口要尽快 ack，避免飞书重投递或长时间阻塞。
- 发送动作统一抽象成 operation，而不是业务层直接调用飞书 API。

详细对标矩阵见：[Codex 飞书通道对标矩阵](CODEX_FEISHU_PARITY_ZH.md)。

## 本项目采用的简化模式

```text
Feishu Gateway
  -> FeishuMessageEvent
  -> BoundedIngressQueue
  -> BetaOrchestratorService
  -> TaskEngine / SQLite
  -> TaskCard
  -> FeishuOperationGateway.apply()
  -> FeishuClient
```

## 为什么要二进程/双层连接器

不建议让飞书 webhook 直接调用完整业务逻辑。

原因：

- 飞书 callback 有响应时间压力。
- 业务逻辑可能慢，例如拉数据、分析、写库。
- 如果同步处理太久，飞书可能重投递。
- 如果没有队列，突发消息容易造成重复任务或刷屏。
- gateway 和业务 worker 分离后，后续更容易重启、限流、灰度。

## 当前已实现

- `FeishuMessageEvent`：统一飞书消息事件。
- `FeishuClient`：发送接口。
- `FeishuOperation`：对标 Codex Operation 的发送操作抽象。
- `FeishuOperationGateway`：对标 Codex Gateway.Apply 的操作应用接口。
- `GuardedOperationGateway`：发送 allowlist 和 operation error 记录。
- `verification_token`：飞书 event callback token 校验。
- `FakeFeishuClient`：测试用发送器。
- `LiveFeishuClient`：真实飞书发送器，默认不启用。
- `send_card`：发送带 `config.update_multi=true` 的飞书 interactive card。
- `update_card`：通过 `message_id` 更新已发送的飞书 interactive card。
- `FeishuWebhookGateway`：本地 event callback gateway 骨架。
- `SQLiteGatewayStateStore`：持久化 gateway counters、去重 key 和 operation errors。
- `run-webhook`：本地 HTTP webhook service。
- `BetaOrchestratorService`：处理 beta 群消息并生成任务卡。
- `BoundedIngressQueue`：按实例隔离的有界入口队列。
- `beta-smoke`：不触达真实飞书的 smoke test。
- `webhook-smoke`：验证 challenge 和 Feishu 风格消息 payload。

## 本地 HTTP 服务

```bash
stock-agent-orchestrator run-webhook --config configs/beta.example.toml --host 127.0.0.1 --port 8787
```

端点：

- `GET /healthz`：返回 `ok` 和 gateway 状态。
- `POST /webhook`

当前仍使用 `FakeFeishuClient`，不会向真实飞书群发送消息。

`run-webhook` 默认会把 gateway runtime state 写入同一个 SQLite db 文件：

- accepted / enqueued / duplicate 计数。
- operation error 计数和最后错误。
- `event_id/message_id` 去重 key。
- operation error 明细。

因此服务重启后，已处理过的飞书事件仍可识别为重复事件。

## 真实发送安全闸

真实发送必须同时满足：

- 配置里 `feishu.send_mode = "live"`
- 配置里有真实 `app_id` / `app_secret`
- CLI 显式传入 `--allow-live-send`
- 项目环境是 `beta`
- 项目模式是 `active`
- `feishu.group_chat_id` 必须在 `feishu.send_allowlist` 内
- `feishu.verification_token` 必须配置

不满足任一条件，都不会向真实飞书群发送消息。

示例：

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.example.toml --allow-live-send
```

真实 beta 前先跑更严格的准入检查：

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example
```

详细步骤见：[飞书 Beta Live Preflight](BETA_LIVE_PREFLIGHT_ZH.md)。

## 下一步真实接入

真实连接器应按这个顺序做：

1. 建 `FeishuGateway`，只接 beta 群。
2. webhook 收到消息后只做解析和入队。
3. worker 从 `BoundedIngressQueue` 拉取事件。
4. 调用 `BetaOrchestratorService` 建任务和发送任务卡。
5. 限频、去重、错误记录。
6. 稳定后持续验证 interactive card update。

## 当前 beta 前安全能力

- `FeishuWebhookGateway` 使用 `event_id/message_id` 做去重，重复事件会 accepted 但不会再次入队。
- `run-webhook` 默认通过 `SQLiteGatewayStateStore` 持久化去重和 operation error，重启后不丢状态。
- `/healthz` 暴露 `connected/degraded`、accepted、enqueued、duplicate、operation error 计数。
- `GuardedOperationGateway` 会拒绝不在 `send_allowlist` 内的 chat_id。
- `FeishuWebhookGateway` 会在配置 `verification_token` 后拒绝 token 不匹配的 callback。
- operation 发送失败会记录到 gateway，并让业务结果返回 `operation_error`，避免 worker 直接崩溃。
- 小智-beta / 小巴-beta 的后续消息可推进同一任务，并发送更新后的任务卡 markdown。
- 小智-beta / 小巴-beta 消息中显式包含 `BETA-0001` 时，会优先绑定该任务，降低多任务并行误更新风险。
- 任务 context 会记录首次和最近一次任务卡 `message_id`。
- 后续任务进展会优先通过 `UPDATE_CARD` 更新同一张任务卡，减少重复刷屏。

## 任务卡更新

真实飞书卡片更新使用官方接口：

```text
PATCH /open-apis/im/v1/messages/:message_id
```

关键约束：

- 初次发送必须是 `interactive` 消息。
- 初次发送和后续更新的卡片都必须包含 `config.update_multi=true`。
- 只能更新当前应用发送、未撤回、仍在可更新期限内的卡片。
- 单条消息更新频控需要在真实 beta 阶段继续观察。

当前限制：

- 还没有飞书 encrypt key 解密和请求签名校验。
- 还没有真正的 rate limit，只有限制入口队列长度。
- interactive card update 已完成本地和请求形态测试，但还没有真实 beta 群验收证据。
- 还没有根据 reply/thread/message_id 绑定原任务卡。

## 安全边界

- beta 阶段只允许 beta 群。
- formal 配置不允许 active。
- 实盘交易永远关闭。
- 新规则必须等待用户审批。
- gateway 层不做选股和分析，只做消息搬运。
