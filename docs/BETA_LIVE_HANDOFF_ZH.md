# 飞书 Beta Live Handoff

`beta-live-handoff` 用来生成真实飞书 beta 验证前的交接单。

它不会联网，不会启动 webhook，不会读取 secret，不会写 `configs/beta.live.toml`，也不会发送飞书消息。它只回答四个问题：

- 用户需要先审批什么。
- 明天需要准备哪些真实飞书字段。
- 哪些字段可以公开说明，哪些字段只能进入环境变量或 ignored 配置。
- 按什么命令顺序跑到 final gate。

## 使用

```bash
stock-agent-orchestrator beta-live-handoff --shell powershell --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

## 交接原则

- 必须使用临时 beta 群，不接当前正式工作流群。
- beta 群建议只放 BOOS、小C-beta、小智-beta、小巴-beta 和必要测试人员。
- beta app 与正式 app 分离。
- `FEISHU_APP_SECRET`、`FEISHU_VERIFICATION_TOKEN`、`FEISHU_ENCRYPT_KEY` 不能贴到群聊、GitHub、README 或截图里。
- `configs/beta.live.toml` 必须保持 ignored，不进入提交。

## 推荐顺序

```bash
stock-agent-orchestrator beta-live-handoff --shell powershell --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

```bash
stock-agent-orchestrator beta-live-intake-checklist --shell powershell --format markdown
```

```bash
stock-agent-orchestrator beta-live-env-template --shell powershell
```

```bash
stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown
```

```bash
stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url https://your-public-domain.example --shell powershell --format markdown
```

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-live-final-gate --config configs/beta.live.toml --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

## 停止条件

- beta 群、beta app、callback URL 任一项不确定。
- 发现目标群是当前正式工作流群。
- 任一 secret 出现在聊天、GitHub 或截图里。
- `configs/beta.live.toml` 没有被 `.gitignore` 保护。
- `beta-live-final-gate` 输出 `ok: false`。
