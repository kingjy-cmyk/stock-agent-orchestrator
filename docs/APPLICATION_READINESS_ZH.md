# 申请完成度检查

## 命令

```bash
stock-agent-orchestrator application-readiness --format markdown
```

## 当前评分规则

总分 100。

- License：8 分
- Python packaging：8 分
- 核心文档：14 分
- 演示与 CLI 文档：12 分
- 测试：12 分
- 飞书连接器：16 分
- 申请材料：12 分
- 真实 beta 验证证据：18 分

## 分档

- `90-100`：`ready_with_evidence`
- `80-89`：`application_ready_but_needs_beta_evidence`
- `60-79`：`promising_but_incomplete`
- `<60`：`not_ready`

## 当前结论

当前仓库已进入 `80+` 档。

但如果没有 `docs/BETA_VALIDATION_REPORT_ZH.md`，不能声称完整 ready。

原因是这个项目的核心主张是：

```text
飞书 beta 群中可验证的透明多 agent 协同。
```

没有真实 beta 群报告，就缺少最关键的外部证据。

## 冲到 90+ 的最短路径

1. 运行 `beta-live-intake-checklist`，确认需要采集的飞书 app、beta 群、open_id、callback 校验字段和本地路径。
2. 运行 `beta-live-prep-dry-run`，确认本地准备链路能跑通。
3. 运行 `init-beta-live-config` 生成本地 `configs/beta.live.toml`，再手工填入真实值；或者用 `beta-live-config-from-env` 从环境变量生成。
4. 运行 `beta-live-config-status`，确认配置存在、已被 `.gitignore` 保护、必要字段已填。
5. 运行 `beta-validation-guide`，确认是否允许进入真实 beta。
6. 运行 `beta-live-runbook`，生成真实 beta 群操作手册和停止条件。
7. 运行 `beta-live-launch-packet`，生成飞书开放平台填写项、首轮测试消息和证据清单。
8. 运行 `beta-live-readiness-bundle`，确认总检查阶段为 `ready_for_real_beta_group_validation`。
9. 运行 `beta-live-evidence-rehearsal`，彩排证据收集和报告生成链路。
10. 启动 `run-webhook --allow-live-send`。
11. 运行 `beta-callback-probe`，确认公网 `/healthz` 和 `/webhook` challenge 可用。
12. 在 beta 群发送 `@小C-beta 今天先给我一份候选池`。
13. 运行 `collect-beta-evidence`，自动保存 `/healthz` 到 `.runtime/healthz.json` 并生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
14. 补任务卡截图或录屏路径。

推荐先运行：

```bash
stock-agent-orchestrator beta-live-intake-checklist --shell powershell --format markdown
```

```bash
stock-agent-orchestrator beta-live-prep-dry-run --format markdown
```

```bash
stock-agent-orchestrator init-beta-live-config --output configs/beta.live.toml
```

```bash
stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown
```

```bash
stock-agent-orchestrator beta-live-config-status --config configs/beta.live.toml --format markdown
```

```bash
stock-agent-orchestrator beta-validation-guide --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-live-runbook --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-live-launch-packet --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

```bash
stock-agent-orchestrator beta-live-evidence-rehearsal --format markdown
```

真实 beta 群跑通后收集证据：

```bash
stock-agent-orchestrator collect-beta-evidence --config configs/beta.live.toml --callback-url https://your-public-domain.example --db .runtime/webhook.db --healthz-json .runtime/healthz.json --report-output docs/BETA_VALIDATION_REPORT_ZH.md --commit <commit>
```

完成后再运行：

```bash
stock-agent-orchestrator application-readiness --format markdown
```

目标结果：

```text
score: 100/100
band: ready_with_evidence
```
