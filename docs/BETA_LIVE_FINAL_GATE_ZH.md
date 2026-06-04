# 飞书 Beta Live Final Gate

`beta-live-final-gate` 是进入真实飞书 beta 群验证前的最后准入门。

它不会启动 webhook，不会联网，不会发送飞书消息，也不会写真实配置。它只聚合四个前置结果：

- `beta-live-config-review`：真实 beta 配置是否存在、被 `.gitignore` 保护、字段完整、敏感字段脱敏。
- `beta-live-readiness-bundle`：本地准备链路、配置、preflight、runbook、启动包是否允许进入真实 beta。
- `beta-callback-deploy-plan`：callback URL 是否为公网 HTTPS，本地监听和飞书事件订阅 URL 是否一致。
- `beta-live-message-script`：首轮 beta 群消息、截图点和失败判据是否明确。

## 使用

```bash
stock-agent-orchestrator beta-live-final-gate --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

如果输出 `ok: false`，不要启动 `run-webhook --allow-live-send`，也不要配置飞书事件订阅或发送 beta 群消息。

如果输出 `stage: ready_to_execute_real_beta_validation`，再按 `Commands` 顺序执行真实 beta 验证。

## 通过后顺序

1. 启动 `run-webhook --allow-live-send`。
2. 运行 `beta-callback-probe`。
3. 在飞书开放平台配置公网 `/webhook` 事件订阅。
4. 按 `beta-live-message-script` 在临时 beta 群发送首轮消息。
5. 截图 beta 群任务卡、飞书开放平台 callback、`/healthz`。
6. 运行 `collect-beta-evidence` 生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
7. 运行 `application-readiness`。

## 必须停止

- final gate 任一 check 为 `fail`。
- readiness bundle 未允许进入真实 beta 群验证。
- callback URL 不是公网 HTTPS。
- 消息会进入当前正式群。
- `/healthz` 出现 `operation_error_count > 0`。
- 真实 beta 配置未通过安全审阅。
