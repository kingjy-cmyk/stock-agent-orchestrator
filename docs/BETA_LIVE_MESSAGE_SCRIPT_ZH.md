# 飞书 Beta Live Message Script

`beta-live-message-script` 用来生成真实 beta 群首轮验收消息脚本。

它不会联网，不会启动 webhook，也不会发送飞书消息。它只输出：

- beta 群中每一步由谁发送。
- 应发送的消息文本。
- 预期任务 ID。
- 预期任务状态。
- 预期任务卡行为。
- 截图或录屏证据点。
- 失败信号和停止条件。

## 使用方式

```bash
stock-agent-orchestrator beta-live-message-script --task-id BETA-0001 --format markdown
```

## 推荐顺序

先完成前置检查：

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --format markdown
```

再生成消息脚本：

```bash
stock-agent-orchestrator beta-live-message-script --task-id BETA-0001 --format markdown
```

发送任何真实 beta 群消息前，先运行最终准入门：

```bash
stock-agent-orchestrator beta-live-final-gate --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

最终准入门通过后，再启动 webhook 并探测 callback：

```bash
stock-agent-orchestrator beta-callback-probe --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

## 首轮消息

1. BOOS 发送：

```text
@小C-beta 今天先给我一份候选池
```

2. 小智-beta 发送：

```text
BETA-0001 七层数据已拉取，等待小巴判断
```

3. 小巴-beta 发送：

```text
BETA-0001 RSI 候选池初判完成，建议进入复盘记录
```

## 成功标准

- SQLite 中存在 `BETA-0001`。
- 任务 context 存在 `task_card_message_id`。
- `task_card_send_count=1`。
- `task_card_update_count>=2`。
- `/healthz` 显示 gateway connected。
- `operation_error_count=0`。
- beta 群截图或录屏覆盖首发任务卡和至少一次原地更新。

## 停止条件

- 任一前置检查失败。
- 首条 BOOS 委托没有生成任务卡。
- 小智-beta 或小巴-beta 后续消息新建了新任务，而不是更新原任务。
- 任务卡更新失败。
- 消息发到了正式群。
