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
- `send_allowlist` 发送白名单
- `message_id/event_id` 内存去重
- `/healthz` gateway 状态
- operation error 记录
- verification token 校验

Stage 2B 剩余：

- 准备 `configs/beta.live.toml`
- 运行 `beta-live-preflight`
- 填真实 beta 群 `chat_id`
- 填小C-beta `open_id`
- 填飞书 app_id / app_secret
- 填 `send_allowlist`
- 填 `verification_token`
- callback 模式准备公网 callback 地址；long_connection 模式准备长链接 SDK 事件绑定
- 在飞书开放平台配置事件订阅
- 真实 beta 群发消息后验证任务卡出现

本轮新增：

- `beta-live-preflight` 命令
- [飞书 Beta Live Preflight](BETA_LIVE_PREFLIGHT_ZH.md)

真实 beta 前安全项已完成 MVP：

- message_id 去重
- gateway state
- send allowlist
- operation error 记录
- verification token 校验

仍需注意：

- 当前去重和 operation error 记录是内存级，服务重启会丢失。
- 长期 daemon 运行前应补持久化状态。

### Stage 3：Task Card Update

状态：`进行中`

目标：

- 小智-beta / 小巴-beta 的回复更新同一任务。
- 支持任务卡状态更新或追加回执。

验收：

- 不重复建任务。
- 状态从 planned 进入 scanning/enriching/analyzing/following_up。
- 任务卡能展示当前责任人变化。

已实现 MVP：

- 小智-beta / 小巴-beta 的后续消息会更新同一 beta 群最新未关闭任务。
- 后续消息不会新建 `BETA-0002`。
- 小巴消息可把每日候选池任务从 `planned` 推进到 `scanning`。
- 更新后会发送新的任务卡 markdown 回执。
- 后续消息显式包含 `BETA-0001` 时，会优先绑定该任务，而不是最新任务。
- 任务 context 会保存 `task_card_message_id`、`latest_task_card_message_id`、`task_card_send_count`。

仍缺：

- 真正的飞书 interactive card `update_card`。
- 根据 reply/thread/message_id 绑定任务卡来源。
- 小C-beta 自身回执的防循环策略还需真实 beta 验证。

### Stage A：Application Materials

状态：`进行中`

目标：

- 让仓库具备申请 Codex 官方活动的评审材料。
- 明确项目一句话、解决的问题、Codex 在项目中的作用。
- 提供本地演示脚本和真实 beta 验证报告模板。

已实现：

- [申请材料草案](APPLICATION_ZH.md)
- [申请完成度检查](APPLICATION_READINESS_ZH.md)
- [演示脚本](DEMO_SCRIPT_ZH.md)
- [飞书 Beta 验证报告模板](BETA_VALIDATION_REPORT_TEMPLATE_ZH.md)
- `collect-beta-evidence` / `beta-validation-report` 命令
- `application-readiness` 命令

仍缺：

- 真实 beta 群截图或 GIF。
- `BETA_VALIDATION_REPORT_ZH.md` 实际验证报告。
- README 顶部效果图。

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
