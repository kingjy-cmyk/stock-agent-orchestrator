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
| Apply operations | 已开始 | `ClientOperationGateway.apply()` | 还缺 update_card 和批量错误处理 |
| Ingress queue | 已完成 MVP | `BoundedIngressQueue` | 后续补持久化和 stale drop |
| Worker/Daemon 分离 | 已完成 MVP | `ConnectorWorker` | 后续补常驻进程状态和优雅关闭 |
| HTTP webhook service | 已完成本地版 | `run-webhook` / `/webhook` / `/healthz` | 还缺公网部署和签名校验 |
| URL verification | 已完成 | challenge 响应 | 后续补飞书 encrypt key 校验 |
| Message event parse | 已完成 MVP | `parse_message_event` | 后续补更多消息类型 |
| Live send client | 已完成安全骨架 | `LiveFeishuClient` | 待真实 beta 群验收 |
| Send safety gate | 已完成 | `send_mode=live` + `--allow-live-send` | 后续补 allowlist 配置 |
| Card action callback | 未完成 | 无 | Stage 3 需要补 |
| Interactive card update | 未完成 | 仅预留 `UPDATE_CARD` | Stage 3 需要补 |
| Message dedupe | 未完成 | 无 | 真实 beta 前必须补 |
| Rate limit | 未完成 | 仅队列上限 | 真实 beta 前必须补 |
| Gateway state | 未完成 | 无 | 真实 beta 前至少补 connected/degraded |
| Multi app / multi gateway | 未完成 | 单 beta gateway | 后续视需要补 |
| File/image/video | 不在 MVP | 无 | 非当前阶段 |

## 当前硬性结论

下一阶段不能只做“能收到 webhook”。

真实 beta 群前至少还要补：

- message_id 去重
- gateway state
- send allowlist
- operation error 记录
- live 配置校验

Stage 3 前必须补：

- card action payload
- update_card
- 任务卡 message_id 绑定到 task context

