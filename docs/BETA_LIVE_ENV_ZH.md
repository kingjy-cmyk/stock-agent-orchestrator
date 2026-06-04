# Beta Live 环境变量配置

`beta-live-config-from-env` 用来从环境变量生成 `configs/beta.live.toml`。

这个方式适合不想手工编辑 TOML，或者想避免把 `app_secret` 写进命令行历史的场景。

## 安全规则

- 目标文件必须已被 `.gitignore` 保护。
- 默认不覆盖已有 `configs/beta.live.toml`。
- 需要覆盖时必须显式加 `--overwrite`。
- 命令输出不会打印 `app_secret`、`verification_token`、`encrypt_key`。

## 需要的环境变量

可以直接生成模板：

```bash
stock-agent-orchestrator beta-live-env-template --shell powershell
```

```powershell
$env:STOCK_AGENT_CANDIDATE_LIST="C:\path\to\candidate_list.md"
$env:STOCK_AGENT_SEVEN_LAYER_REPORTS="C:\path\to\seven_layer"
$env:STOCK_AGENT_ENTRY_MONITOR_REPORTS="C:\path\to\entry_monitor"
$env:STOCK_AGENT_SQLITE_DB="./runtime/beta-live.db"
$env:FEISHU_GROUP_CHAT_ID="oc_xxx"
$env:FEISHU_OWNER_OPEN_ID="ou_xiaoc_beta"
$env:FEISHU_DATA_OPEN_ID="ou_xiaozhi_beta"
$env:FEISHU_ANALYST_OPEN_ID="ou_xiaoba_beta"
$env:FEISHU_APP_ID="cli_xxx"
$env:FEISHU_APP_SECRET="<secret>"
$env:FEISHU_VERIFICATION_TOKEN="<token>"
$env:FEISHU_ENCRYPT_KEY="<encrypt-key>"
$env:FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE="60"
```

## 写入配置

```bash
stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown
```

写入后检查：

```bash
stock-agent-orchestrator beta-live-config-status --config configs/beta.live.toml --format markdown
```

如果 `ready_for_preflight = true`，再进入：

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```
