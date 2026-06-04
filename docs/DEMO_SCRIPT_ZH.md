# 演示脚本

## 目标

这份脚本用于给评审或新用户快速展示仓库价值。

它分两层：

- 本地演示：证明仓库可安装、可运行、可生成任务闭环。
- 飞书 beta 演示：证明真实透明协同可在飞书群里被用户核实。

## 本地演示

### 1. 安装

```bash
python -m pip install -e .
```

### 2. 环境检查

```bash
stock-agent-orchestrator doctor
```

期望：

- `ok = true`
- `.runtime` 可写

### 3. 一键 demo

```bash
stock-agent-orchestrator demo
```

期望：

- 生成 demo shadow sample。
- 生成 demo report。
- 能看到任务被创建、推进或等待用户。

### 4. Fake 飞书委托

```bash
stock-agent-orchestrator beta-smoke --config configs/beta.example.toml
```

期望：

- `handled = true`
- `task_id = BETA-0001`
- `sent_messages[0].text` 里出现任务卡。

### 5. Webhook smoke

```bash
stock-agent-orchestrator webhook-smoke --config configs/beta.example.toml
```

期望：

- challenge 被接受。
- 飞书风格消息 payload 被解析。
- worker 处理 1 条委托。
- fake client 生成任务卡。

### 6. Live preflight

示例配置必须失败，因为它包含占位符：

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.example.toml --callback-url https://agent-beta.example.com
```

期望：

- `ok = false`
- 失败项包含 `no_required_placeholders`
- 失败项包含 `feishu.app_id` 或 `feishu.verification_token`

这证明真实发送不会被误开启。

## 飞书 beta 演示

前提：

- 有独立 beta 飞书群。
- 有 beta 飞书应用。
- 有公网 https callback。
- `configs/beta.live.toml` 已填真实值。

### 1. 检查 live 配置状态

```bash
stock-agent-orchestrator beta-live-config-status --config configs/beta.live.toml --format markdown
```

期望：

- `exists = true`
- `gitignored = true`
- `ready_for_preflight = true`
- secret 字段显示 `<redacted>`

### 2. 跑 preflight

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

期望：

- `ok = true`
- 输出 `webhook_url`
- 输出 `healthz_url`

### 3. 生成 live runbook

```bash
stock-agent-orchestrator beta-live-runbook --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

期望：

- `ready_to_start = true`
- 输出 `Commands`
- 输出 `Stop Conditions`

### 4. 启动 webhook

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.toml --allow-live-send
```

### 5. 配置飞书事件订阅

把 preflight 输出的 `webhook_url` 填到飞书开放平台事件订阅 callback。

### 6. 在 beta 群委托

```text
@小C-beta 今天先给我一份候选池
```

期望：

- beta 群出现 `BETA-0001` 任务卡。
- 任务卡展示目标、意图、状态、当前责任人、审批状态。

### 6.1 Agent 后续消息

让小巴-beta 在同一 beta 群回复：

```text
BETA-0001 候选池已筛出，RSI<35 共 3 只
```

期望：

- 不创建 `BETA-0002`。
- `BETA-0001` 状态推进到 `scanning`。
- 群里出现更新后的任务卡 markdown。
- 如果 beta 群里有多个任务，消息中的 `BETA-0001` 会优先作为绑定依据。

### 7. 检查健康状态

访问：

```text
https://your-public-domain.example/healthz
```

期望：

- `status = connected`
- `operation_error_count = 0`
- `duplicate_count` 没有异常增长

### 8. 收集证据并生成验证报告

```bash
stock-agent-orchestrator collect-beta-evidence \
  --config configs/beta.live.toml \
  --callback-url https://your-public-domain.example \
  --commit <commit> \
  --db .runtime/webhook.db \
  --task-id BETA-0001 \
  --healthz-json .runtime/healthz.json \
  --beta-group-name "Stock Agent Beta" \
  --feishu-app-name "stock-agent-orchestrator-beta" \
  --report-output docs/BETA_VALIDATION_REPORT_ZH.md
```

期望：

- `总体通过 = true`
- `preflight 通过 = true`
- `任务存在 = true`
- `healthz 正常 = true`

## 录屏建议

录屏可以按这个顺序：

- README 项目标题和目标。
- `doctor` 通过。
- `beta-smoke` 生成任务卡。
- `beta-live-preflight` 示例失败，说明安全闸有效。
- 真实 beta 群里发 `@小C-beta 今天先给我一份候选池`。
- beta 群出现任务卡。
- `/healthz` 状态正常。

## 演示边界说明

本项目当前演示重点是：

- 多 agent 协作透明化。
- 任务 owner 持续跟进。
- 飞书作为控制面。
- 安全接入真实 beta 群。

当前不演示：

- 实盘交易。
- 自动下单。
- 股票收益承诺。
- 完整 interactive card update。
