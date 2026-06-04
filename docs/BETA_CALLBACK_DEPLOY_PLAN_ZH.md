# 飞书 Beta Callback Deploy Plan

`beta-callback-deploy-plan` 用来在启动真实 webhook 前生成公网 callback 部署预案。

它不会联网，不会启动 webhook，也不会发送飞书消息。它只根据本地监听地址和公网 callback URL 输出：

- 本地监听地址。
- 飞书事件订阅应填写的 `/webhook` URL。
- `/healthz` 探测 URL。
- `run-webhook`、`beta-callback-probe`、`collect-beta-evidence` 命令。
- 飞书开放平台配置步骤。
- 证据清单和停止条件。

## 使用方式

```bash
stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --format markdown
```

如果本地端口不是默认值：

```bash
stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --host 127.0.0.1 --port 8787 --format markdown
```

## 通过标准

- callback URL 必须是公网 `https`。
- 不能使用 `localhost`、`127.0.0.1`、`.local` 或 `http` 作为飞书事件订阅地址。
- `/webhook` 和 `/healthz` 必须转发到同一个本地 `run-webhook` 服务。
- `run-webhook`、`beta-callback-probe`、`collect-beta-evidence` 必须使用同一份 config 和 db。

## 推荐顺序

```bash
stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.toml --db .runtime/webhook.db --host 127.0.0.1 --port 8787 --allow-live-send
```

```bash
stock-agent-orchestrator beta-callback-probe --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

## 停止条件

- callback URL 不是公网 `https`。
- 飞书开放平台填的是 localhost 或 http。
- `beta-callback-probe` 失败。
- `/healthz` 出现 `operation_error_count > 0`。
- `run-webhook` 和 `collect-beta-evidence` 使用了不同 db。
