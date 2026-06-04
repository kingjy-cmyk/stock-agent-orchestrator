# 飞书连接器架构

## 参考来源

本项目的飞书连接器设计参考当前 Codex 飞书通道的二进程模式，但不照搬实现。

Codex 飞书通道里的关键模式是：

- `Gateway` 只负责平台接入：启动、接收飞书事件、发送 operations。
- `Daemon / Worker` 负责业务处理：状态、任务、运行时、恢复。
- 中间用 ingress queue 隔离入口和业务处理。
- 入口要尽快 ack，避免飞书重投递或长时间阻塞。
- 发送动作统一抽象成 operation，而不是业务层直接调用飞书 API。

## 本项目采用的简化模式

```text
Feishu Gateway
  -> FeishuMessageEvent
  -> BoundedIngressQueue
  -> BetaOrchestratorService
  -> TaskEngine / SQLite
  -> TaskCard
  -> FeishuClient.send_message()
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
- `FakeFeishuClient`：测试用发送器。
- `FeishuWebhookGateway`：本地 event callback gateway 骨架。
- `BetaOrchestratorService`：处理 beta 群消息并生成任务卡。
- `BoundedIngressQueue`：按实例隔离的有界入口队列。
- `beta-smoke`：不触达真实飞书的 smoke test。
- `webhook-smoke`：验证 challenge 和 Feishu 风格消息 payload。

## 下一步真实接入

真实连接器应按这个顺序做：

1. 建 `FeishuGateway`，只接 beta 群。
2. webhook 收到消息后只做解析和入队。
3. worker 从 `BoundedIngressQueue` 拉取事件。
4. 调用 `BetaOrchestratorService` 建任务和发送任务卡。
5. 限频、去重、错误记录。
6. 稳定后再考虑 interactive card update。

## 安全边界

- beta 阶段只允许 beta 群。
- formal 配置不允许 active。
- 实盘交易永远关闭。
- 新规则必须等待用户审批。
- gateway 层不做选股和分析，只做消息搬运。
