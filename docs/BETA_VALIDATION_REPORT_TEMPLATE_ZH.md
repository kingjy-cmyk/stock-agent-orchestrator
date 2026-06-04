# 飞书 Beta 验证报告模板

## 基本信息

- 日期：
- 验证人：
- 仓库 commit：
- beta 群名称：
- 飞书应用：
- callback URL：

## 配置检查

运行命令：

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

结果：

- `ok`：
- 失败项：
- 备注：

## Webhook 启动

运行命令：

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.toml --allow-live-send
```

结果：

- 服务是否启动：
- `webhook_url`：
- `healthz_url`：

## 飞书群委托

发送内容：

```text
@小C-beta 今天先给我一份候选池
```

结果：

- 是否出现任务卡：
- 任务 ID：
- 当前责任人：
- 是否等待审批：

## 健康状态

访问 `/healthz`。

结果：

- `status`：
- `accepted_count`：
- `enqueued_count`：
- `duplicate_count`：
- `operation_error_count`：
- `last_error`：

## 截图或录屏

- beta 群委托截图：
- 任务卡截图：
- healthz 截图：

## 结论

- 是否通过真实 beta 最小闭环：
- 是否可进入 Stage 3：
- 需要修复的问题：
