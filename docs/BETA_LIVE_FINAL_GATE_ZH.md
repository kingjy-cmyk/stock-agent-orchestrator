# 飞书 Beta Live Final Gate

`beta-live-final-gate` 是进入真实飞书 beta 群验证前的最后准入门。

它不会启动 webhook，不会联网，不会发送飞书消息，也不会写真实配置。它只聚合四个前置结果：

- `beta-live-config-review`：真实 beta 配置是否存在、被 `.gitignore` 保护、字段完整、敏感字段脱敏。
- `beta-live-readiness-bundle`：本地准备链路、配置、preflight、runbook、启动包是否允许进入真实 beta。
- `transport_plan`：callback 模式检查公网 HTTPS；long_connection 模式检查长链接接入路径。
- `beta-live-message-script`：首轮 beta 群消息、截图点和失败判据是否明确。

## 使用

先运行总控台，确认当前 stage 和下一步：

```bash
stock-agent-orchestrator beta-live-control-panel --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

先生成真实 beta 交接单，确认用户审批点和 secret 边界：

```bash
stock-agent-orchestrator beta-live-handoff --shell powershell --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

再运行最终准入门：

```bash
stock-agent-orchestrator beta-live-final-gate --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

如果输出 `ok: false`，不要启动 `run-webhook --allow-live-send`，也不要配置飞书事件订阅或发送 beta 群消息。

如果输出 `stage: ready_to_execute_real_beta_validation`，再按 `Commands` 顺序执行真实 beta 验证。

## 通过后顺序

1. callback 模式启动 `run-webhook --allow-live-send`；long_connection 模式启动 `run-long-connection --allow-live-send`。
2. callback 模式运行 `beta-callback-probe`；long_connection 模式不需要公网 probe。
3. 在飞书开放平台启用对应事件订阅模式。
4. 按 `beta-live-message-script` 在临时 beta 群发送首轮消息。
5. 截图 beta 群任务卡、飞书开放平台 callback、`/healthz`。
6. 运行 `collect-beta-evidence` 生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
7. 运行 `application-readiness`。

## 必须停止

- final gate 任一 check 为 `fail`。
- readiness bundle 未允许进入真实 beta 群验证。
- callback 模式下 callback URL 不是公网 HTTPS。
- long_connection 模式下长链接接收器启动失败。
- 消息会进入当前正式群。
- `/healthz` 出现 `operation_error_count > 0`。
- 真实 beta 配置未通过安全审阅。
