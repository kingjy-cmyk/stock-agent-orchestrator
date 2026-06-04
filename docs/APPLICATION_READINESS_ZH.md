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

1. 运行 `init-beta-live-config` 生成本地 `configs/beta.live.toml`，再填入真实值。
2. 运行 `beta-validation-guide`，确认是否允许进入真实 beta。
3. 跑通 `beta-live-preflight`。
4. 启动 `run-webhook --allow-live-send`。
5. 运行 `beta-callback-probe`，确认公网 `/healthz` 和 `/webhook` challenge 可用。
6. 在 beta 群发送 `@小C-beta 今天先给我一份候选池`。
7. 运行 `collect-beta-evidence`，自动保存 `/healthz` 到 `.runtime/healthz.json` 并生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
8. 补任务卡截图或录屏路径。

推荐先运行：

```bash
stock-agent-orchestrator init-beta-live-config --output configs/beta.live.toml
```

```bash
stock-agent-orchestrator beta-validation-guide --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
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
