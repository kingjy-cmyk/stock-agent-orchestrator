# 长线推进任务

## 目标

把 `stock-agent-orchestrator` 按阶段推进成可在飞书 beta 群验证的多 agent 透明协同系统。

推进方式：

- 每次完成一个完整阶段。
- 阶段完成后集中反馈已知问题。
- 下一阶段再根据用户意见调整。

## 阶段划分

### Stage 1：Connector Worker

状态：`已完成`

目标：

- 不接真实飞书群。
- 完成 `gateway event -> ingress queue -> worker -> orchestrator -> task card send request`。
- 让连接器从单次 smoke 变成可批量消费事件。

验收：

- fake beta 消息可以入队。
- worker 可以批量消费。
- 有效委托创建任务并生成任务卡。
- 非委托消息被忽略。
- 队列处理后深度归零。

已实现：

- `ConnectorWorker`
- `worker-smoke`
- worker 单元测试

### Stage 2：Real Beta Gateway

状态：`进行中`

目标：

- 接入真实 beta 群消息输入。
- 只允许 beta 群。
- 只发送任务卡，不做复杂状态更新。

验收：

- beta 群 @小C-beta 后出现任务卡。
- 非 beta 群消息被拒绝。
- formal 配置不能 active。

本阶段先分两步：

- Stage 2A：本地 webhook gateway 骨架，支持 challenge、HTTP service 和消息 payload 入队。
- Stage 2B：填入真实 beta 群凭证和公网回调地址后，接真实 beta 群。

Stage 2A 已实现：

- `FeishuWebhookGateway`
- `run-webhook`
- `/healthz`
- `/webhook`
- challenge 响应
- Feishu 风格消息 payload 入队
- fake send 任务卡
- `LiveFeishuClient` 真实发送安全骨架
- live 发送必须显式 `--allow-live-send`

Stage 2B 剩余：

- 对标 Codex 飞书通道补齐真实 beta 前安全项
- 准备 `configs/beta.live.toml`
- 填真实 beta 群 `chat_id`
- 填小C-beta `open_id`
- 填飞书 app_id / app_secret
- 准备公网 callback 地址
- 在飞书开放平台配置事件订阅
- 真实 beta 群发消息后验证任务卡出现

真实 beta 前必须补：

- message_id 去重
- gateway state
- send allowlist
- operation error 记录

### Stage 3：Task Card Update

状态：`待开始`

目标：

- 小智-beta / 小巴-beta 的回复更新同一任务。
- 支持任务卡状态更新或追加回执。

验收：

- 不重复建任务。
- 状态从 planned 进入 scanning/enriching/analyzing/following_up。
- 任务卡能展示当前责任人变化。

### Stage 4：Daily Candidate Chain

状态：`待开始`

目标：

- 跑通每日候选池最小闭环。
- 候选池导入后形成证据。
- 小C-beta 能收口或进入 WAITING_USER。

验收：

- 一条候选池链路能从委托到落盘。
- 缺证据时不关闭。
- 新规则不自动生效。

### Stage 5：Seven-Layer Research Chain

状态：`待开始`

目标：

- 跑通单票七层研究卡。
- 固定七层字段和缺失标记。
- 小智-beta / 小巴-beta 责任边界清晰。

验收：

- 单票任务能输出标准七层卡。
- 缺字段可见。
- 分析结论有证据。

## 当前阶段完成后需要反馈的问题

Stage 1 完成后应反馈：

- worker 运行方式是否继续用 CLI smoke，还是开始准备真实服务进程。
- beta 群真实接入用现有 relay，还是单独 webhook/event callback。
- 任务卡先发 markdown 文本，还是直接做飞书 interactive card。
