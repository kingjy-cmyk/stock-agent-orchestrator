# 飞书 Beta Live Config Review

`beta-live-config-review` 用于真实 beta 配置填写后的安全自审。

它只读取并脱敏展示配置状态：

- 不联网。
- 不启动 webhook。
- 不发送飞书消息。
- 不输出 `app_secret`、`verification_token`、`encrypt_key`。
- 不修改 `configs/beta.live.toml`。

## 使用方式

```bash
stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

## 通过标准

- `configs/beta.live.toml` 存在。
- 配置文件被 `.gitignore` 保护。
- 敏感字段在输出中只显示为 `<redacted>` 或占位符。
- 所有必填字段已填写。
- `ready_for_preflight=true`。

## 何时停止

- `gitignored=false` 时停止。
- `ready_for_preflight=false` 时停止。
- 任意真实 secret 出现在输出中时停止。
- `chat_id` 或 `open_id` 不能确认属于临时 beta 群时停止。

## 推荐顺序

```bash
stock-agent-orchestrator beta-live-intake-checklist --shell powershell --format markdown
```

```bash
stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown
```

```bash
stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```
