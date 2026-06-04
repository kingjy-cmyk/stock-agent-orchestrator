# 飞书 Beta Live Preflight

## 目的

`beta-live-preflight` 是进入真实飞书 beta 群前的硬性准入检查。

它不会连接真实飞书，也不会发送消息。它只判断当前配置和公网 callback 是否已经满足主动 beta 验证的最低条件。

## 使用方式

先从示例复制一份真实配置文件：

```bash
copy configs\beta.live.example.toml configs\beta.live.toml
```

填入真实值：

- `feishu.group_chat_id`
- `feishu.owner_open_id`
- `feishu.data_open_id`
- `feishu.analyst_open_id`
- `feishu.app_id`
- `feishu.app_secret`
- `feishu.send_allowlist`
- `feishu.verification_token`
- `feishu.encrypt_key`
- `paths.candidate_list`
- `paths.seven_layer_reports`
- `paths.entry_monitor_reports`

然后运行：

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example
```

Markdown 输出：

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

## 通过条件

必须全部通过：

- 配置没有 error。
- 项目是 `beta active`。
- `feishu.send_mode = "live"`。
- `feishu.group_chat_id` 在 `feishu.send_allowlist` 内。
- 实盘交易关闭。
- 新规则必须用户审批。
- 必填字段没有占位符。
- `feishu.verification_token` 已配置，用于飞书 callback token 校验。
- `feishu.encrypt_key` 已配置，用于 `X-Lark-Signature` 请求签名校验和 encrypt payload 解密。
- callback URL 是公网 `https`。

## 通过后怎么做

preflight 通过后，再启动真实发送服务：

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.toml --allow-live-send
```

把 preflight 输出里的 `webhook_url` 填到飞书开放平台事件订阅 callback。

然后在 beta 群发一条最小委托：

```text
@小C-beta 今天先给我一份候选池
```

验收：

- beta 群出现 `BETA-0001` 任务卡。
- `/healthz` 显示 `operation_error_count = 0`。
- 重复投递不会重复建任务。

## 当前限制

- 该命令只做本地静态准入检查，不探测公网 URL 是否真的可访问。
- 已支持飞书 event callback verification token 校验。
- 已支持基于 `encrypt_key` 的 `X-Lark-Signature` 请求签名校验。
- 已支持飞书 encrypt payload 解密。
- 去重和 operation error 记录已持久化到 SQLite。
