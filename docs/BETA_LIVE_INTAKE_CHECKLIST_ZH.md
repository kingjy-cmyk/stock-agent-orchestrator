# 飞书 Beta Live Intake Checklist

`beta-live-intake-checklist` 用来在填写真实 beta 配置前，列出必须收集的飞书字段和本地路径。

它只生成清单：

- 不联网。
- 不启动 webhook。
- 不读取 secret。
- 不写 `configs/beta.live.toml`。
- 不发送飞书消息。

## 使用方式

PowerShell：

```bash
stock-agent-orchestrator beta-live-intake-checklist --shell powershell --format markdown
```

Bash：

```bash
stock-agent-orchestrator beta-live-intake-checklist --shell bash --format markdown
```

## 清单覆盖内容

- 本地候选池路径。
- 七层数据报告目录。
- 入场监控报告目录。
- beta SQLite 数据库路径。
- beta 群 `open_chat_id`。
- `小C-beta / 小智-beta / 小巴-beta` 的 `open_id`。
- 飞书应用 `app_id`。
- 飞书应用 `app_secret`。
- 事件订阅 `verification_token`。
- 事件订阅 `encrypt_key`。

## 核心原则

- 必须使用临时 beta 群，不接当前正式工作流群。
- `app_secret`、`verification_token`、`encrypt_key` 只能进入环境变量或 ignored 配置文件。
- `configs/beta.live.toml` 必须先被 `.gitignore` 保护。
- 不确定 `chat_id` 或 `open_id` 时停止，不继续接入。

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
stock-agent-orchestrator beta-live-config-status --config configs/beta.live.toml --format markdown
```

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```
