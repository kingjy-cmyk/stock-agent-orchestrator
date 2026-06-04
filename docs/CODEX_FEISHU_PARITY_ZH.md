# Codex 飞书通道对标矩阵

## 对标原则

`stock-agent-orchestrator` 的飞书连接器必须对标当前 Codex 飞书通道的连接器能力，而不是只做一个简单 webhook。

参考仓库：

- `C:\Users\Jy95\.codex\workspace-feishu\my-feishu-codex`

关键参考文件：

- `internal/adapter/feishu/gateway.go`
- `internal/adapter/feishu/projector.go`
- `internal/adapter/feishu/gateway_runtime.go`
- `internal/app/daemon/ingress.go`
- `internal/runtime/daemon_process.go`

## 能力矩阵

| Codex 飞书通道能力 | 本仓库当前状态 | 当前实现 | 后续缺口 |
|---|---|---|---|
| Gateway 抽象 | 部分完成 | `FeishuWebhookGateway` | 还缺真实多 gateway 管理 |
| Operation 抽象 | 已开始 | `FeishuOperation` / `FeishuOperationGateway` | 还缺完整 card/image/reaction/delete |
| Apply operations | 已完成 MVP | `ClientOperationGateway.apply()` | 还缺批量错误处理和更多 operation 类型 |
| Ingress queue | 已完成 MVP | `BoundedIngressQueue` | 后续补持久化和 stale drop |
| Worker/Daemon 分离 | 已完成 MVP | `ConnectorWorker` | 后续补常驻进程状态和优雅关闭 |
| HTTP webhook service | 已完成本地版 | `run-webhook` / `/webhook` / `/healthz` | 还缺公网部署和 encrypt payload 解密 |
| URL verification | 已完成 | challenge 响应 + verification token 校验 + `X-Lark-Signature` 校验 | 后续补飞书 encrypt payload 解密 |
| Message event parse | 已完成 MVP | `parse_message_event` | 后续补更多消息类型 |
| Live send client | 已完成安全骨架 | `LiveFeishuClient` | 待真实 beta 群验收 |
| Send safety gate | 已完成 MVP | `send_mode=live` + `--allow-live-send` + `send_allowlist` | 后续补更细的 per-agent 权限 |
| Card action callback | 未完成 | 无 | Stage 3 需要补 |
| Interactive card update | 已完成 MVP | `SEND_CARD` 发送 updateable interactive card，`UPDATE_CARD` 通过 `message_id` 更新 | 待真实 beta 群验收 |
| Message dedupe | 已完成 MVP | `FeishuWebhookGateway` + `SQLiteGatewayStateStore` 持久化去重 | 后续补 stale drop |
| Rate limit | 未完成 | 仅队列上限 | 真实 beta 前必须补 |
| Gateway state | 已完成 MVP | `/healthz` 暴露 `connected/degraded` 和计数 | 后续补 daemon 级心跳 |
| Operation error 记录 | 已完成 MVP | `GuardedOperationGateway` + `SQLiteGatewayStateStore` 持久化错误表 | 后续补错误恢复策略 |
| Multi app / multi gateway | 未完成 | 单 beta gateway | 后续视需要补 |
| File/image/video | 不在 MVP | 无 | 非当前阶段 |

## 当前硬性结论

下一阶段不能只做“能收到 webhook”，必须证明 beta 群链路的输入、去重、状态、发送安全闸都工作。

本轮已补真实 beta 前安全 MVP：

- message_id 去重
- gateway state
- send allowlist
- operation error 记录
- live 配置校验

仍然缺：

- 公网 callback 部署
- 飞书事件订阅配置
- 飞书 encrypt payload 解密
- rate limit 细化

已补齐：

- 去重 key 持久化
- gateway counters 持久化
- operation error 明细持久化
- gateway 重启后重复事件不再入队
- 基于 `encrypt_key` 的 `X-Lark-Signature` 请求签名校验

Stage 3 已补：

- update_card
- 任务卡 message_id 绑定到 task context
- 小智/小巴后续进展优先更新同一张任务卡

Stage 3 后续仍需补：

- card action payload
- reply/thread/message_id 到 task_id 的绑定
- 真实 beta 群验收报告
