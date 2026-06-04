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
- `FakeFeishuClient`：测试用发送器。
- `LiveFeishuClient`：真实飞书发送器，默认不启用。
- `FeishuWebhookGateway`：本地 event callback gateway 骨架。
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

## 真实发送安全闸

真实发送必须同时满足：

- 配置里 `feishu.send_mode = "live"`
- 配置里有真实 `app_id` / `app_secret`
- CLI 显式传入 `--allow-live-send`
- 项目环境是 `beta`
- 项目模式是 `active`
- `feishu.group_chat_id` 必须在 `feishu.send_allowlist` 内

不满足任一条件，都不会向真实飞书群发送消息。

示例：

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.example.toml --allow-live-send
```

## 下一步真实接入

真实连接器应按这个顺序做：

1. 建 `FeishuGateway`，只接 beta 群。
2. webhook 收到消息后只做解析和入队。
3. worker 从 `BoundedIngressQueue` 拉取事件。
4. 调用 `BetaOrchestratorService` 建任务和发送任务卡。
5. 限频、去重、错误记录。
6. 稳定后再考虑 interactive card update。

## 当前 beta 前安全能力

- `FeishuWebhookGateway` 使用 `event_id/message_id` 做内存去重，重复事件会 accepted 但不会再次入队。
- `/healthz` 暴露 `connected/degraded`、accepted、enqueued、duplicate、operation error 计数。
- `GuardedOperationGateway` 会拒绝不在 `send_allowlist` 内的 chat_id。
- operation 发送失败会记录到 gateway，并让业务结果返回 `operation_error`，避免 worker 直接崩溃。

当前限制：

- 去重和错误记录是内存级，服务重启后会丢失。
- 还没有飞书签名 / encrypt key 校验。
- 还没有真正的 rate limit，只有限制入口队列长度。

## 安全边界

- beta 阶段只允许 beta 群。
- formal 配置不允许 active。
- 实盘交易永远关闭。
- 新规则必须等待用户审批。
- gateway 层不做选股和分析，只做消息搬运。
