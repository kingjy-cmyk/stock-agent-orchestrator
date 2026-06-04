# 飞书 Beta Live Runbook

`beta-live-runbook` 用来生成真实 beta 群验证的可执行操作手册。

它不会启动 webhook，也不会发送飞书消息。它会读取真实 beta 配置和 callback URL，然后输出：

- 当前是否可以开始真实 beta 群验证。
- 应按什么顺序运行命令。
- 哪些步骤必须人工完成。
- 遇到哪些情况必须停止。
- 最终需要收集哪些证据。

## 生成 Runbook

```bash
stock-agent-orchestrator beta-live-runbook --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

如果输出 `ready_to_start: false`，不要启动 `run-webhook --allow-live-send`。

如果输出 `ready_to_start: true`，按 `Commands` 顺序执行。

## 推荐顺序

1. 运行 `init-beta-live-config` 生成本地真实配置。
2. 手工填入真实值，或运行 `beta-live-config-from-env` 从环境变量生成真实配置。
3. 准备公网 HTTPS callback。
4. 运行 `beta-live-config-status`，确认没有占位符且 secret 已脱敏显示。
5. 运行 `beta-live-runbook`。
6. 运行 `beta-live-launch-packet`，生成飞书开放平台填写项、首轮测试消息和证据清单。
7. 运行 `beta-callback-deploy-plan`，确认公网 callback、飞书事件订阅 URL、本地监听和探测命令一致。
8. 运行 `beta-live-message-script`，确认首轮消息、截图点和失败判据。
9. 如果 runbook、launch packet、deploy plan 和 message script 都允许开始，再启动 `run-webhook --allow-live-send`。
10. 运行 `beta-callback-probe`。
11. 在飞书开放平台配置事件订阅 webhook URL。
12. 在 beta 群按 message script 发送首轮消息。
13. 确认任务卡出现并可被后续消息原地更新。
14. 运行 `collect-beta-evidence` 生成验证报告。
15. 运行 `application-readiness`。

## 必须停止的情况

- `beta-live-runbook` 显示 `ready_to_start: false`。
- `beta-callback-deploy-plan` 显示 `ok: false`。
- `beta-live-message-script` 中任一前置命令失败。
- `beta-callback-probe` 失败。
- beta 群没有出现任务卡。
- `collect-beta-evidence` 报告里 `task_card_message_id` 缺失。
- `/healthz` 中 `operation_error_count > 0`。
- 任意实盘交易配置被打开。

## 成功标准

- beta 群中能看到 BOOS 委托。
- 群里出现 `BETA-*` 任务卡。
- 小智-beta / 小巴-beta 后续消息能更新同一张任务卡。
- `.runtime/healthz.json` 显示 gateway connected 且 operation error 为 0。
- `docs/BETA_VALIDATION_REPORT_ZH.md` 生成并通过。
