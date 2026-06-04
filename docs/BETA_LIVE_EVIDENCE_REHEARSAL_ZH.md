# 飞书 Beta Evidence Rehearsal

`beta-live-evidence-rehearsal` 用来彩排真实 beta 验证后的证据收集链路。

它不会联网，不会连接真实飞书，也不会启动 webhook。它会在本地生成：

- 彩排配置文件。
- 彩排 SQLite 任务库。
- 模拟 `/healthz` JSON。
- 彩排版 `BETA_VALIDATION_REPORT_REHEARSAL_ZH.md`。

默认输出目录：

```text
.runtime/beta-evidence-rehearsal/
```

该目录已被 `.gitignore` 忽略。

## 使用方式

```bash
stock-agent-orchestrator beta-live-evidence-rehearsal --format markdown
```

也可以指定目录：

```bash
stock-agent-orchestrator beta-live-evidence-rehearsal --runtime-dir .runtime/my-rehearsal --format markdown
```

## 目的

这个命令证明：

- SQLite 里存在 `BETA-*` 任务时，报告可以读取任务。
- 任务 context 里存在 `task_card_message_id` 时，报告能证明任务卡已落库。
- `/healthz` 正常时，报告能通过健康检查。
- `collect-beta-evidence` 的报告生成链路可以跑通。

## 不能做什么

- 不能证明真实飞书 beta 群可用。
- 不能替代 `docs/BETA_VALIDATION_REPORT_ZH.md`。
- 不能作为 Codex 官方活动申请证据。
- 不能绕过真实 `beta-live-readiness-bundle`、`beta-callback-probe` 和真实截图。

## 下一步

彩排通过后，继续：

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

真实 beta 群跑通后再运行：

```bash
stock-agent-orchestrator collect-beta-evidence --config configs/beta.live.toml --callback-url https://your-public-domain.example --db .runtime/webhook.db --healthz-json .runtime/healthz.json --report-output docs/BETA_VALIDATION_REPORT_ZH.md --commit <commit>
```
