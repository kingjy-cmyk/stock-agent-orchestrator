# 飞书 Beta Live Launch Packet

`beta-live-launch-packet` 用来生成真实 beta 群启动包。

它不会启动 webhook，也不会发送飞书消息。它读取真实 beta 配置和事件接入信息，然后输出：

- 飞书开放平台需要填写的 callback 和事件订阅信息。
- beta 群隔离状态。
- `小C-beta / 小智-beta / 小巴-beta` 的角色名单。
- 首轮测试消息。
- 审批门槛、停止条件和证据清单。
- 真实 beta 验证需要执行的命令。

## 生成启动包

```bash
stock-agent-orchestrator beta-live-launch-packet --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

如果输出 `ready_to_launch: false`，不要启动 `run-webhook --allow-live-send`，也不要把 callback 接到真实飞书应用。

如果输出 `ready_to_launch: true`，再按 `Commands` 和 `Test Messages` 执行 beta 群验证。

## 和 Runbook 的区别

`beta-live-runbook` 偏命令顺序和停止条件。

`beta-live-launch-packet` 偏临场执行包，重点回答：

- 飞书开放平台到底填什么。
- beta 群里第一轮发什么消息。
- 需要截哪些图。
- 哪些审批门槛必须满足。
- 哪些信息不能泄露。

## 成功标准

- `preflight_ok=true`。
- `beta_group_isolated=true`。
- `ready_to_launch=true`。
- 任务卡只发到 beta 群。
- 小智-beta / 小巴-beta 能更新同一张任务卡。
- `collect-beta-evidence` 生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
- 长链接模式不需要公网 callback；callback 模式才需要公网 URL。

## 安全边界

- 输出不会渲染 `app_secret`、`verification_token`、`encrypt_key`。
- `allow_real_trading` 必须为 `false`。
- `group_chat_id` 必须在 `send_allowlist` 中。
- beta 阶段不允许连接正式群。
