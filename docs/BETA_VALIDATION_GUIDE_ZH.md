# 飞书 Beta 验收向导

`beta-validation-guide` 用来把真实 beta 群验收步骤串起来。

它不会启动 webhook，也不会发送飞书消息。它只读取配置、callback URL 和仓库状态，然后告诉你当前是否可以进入真实 beta 群验证。

## 什么时候使用

在准备进入真实 beta 群前运行：

```bash
stock-agent-orchestrator beta-validation-guide --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

## 输出内容

向导会输出：

- 当前阶段。
- readiness 评分。
- `beta-live-preflight` 是否通过。
- webhook URL 和 healthz URL。
- 当前应该执行的检查清单。
- 下一步命令。
- 需要收集的截图、录屏和 JSON 证据。
- 风险提示。

## 安全规则

如果 preflight 没通过，向导不会展示 `run-webhook --allow-live-send` 命令。

这条规则是为了避免配置还没准备好时误触真实 beta 群。

## 推荐顺序

1. 运行 `init-beta-live-config` 生成本地 `configs/beta.live.toml`。
2. 运行 `beta-validation-guide`。
3. 如果向导显示 `fix_preflight_before_live_beta`，先修配置。
4. 如果向导显示 `run_live_beta_and_collect_evidence`，先运行 `beta-live-runbook`。
5. 按 runbook 启动 `run-webhook --allow-live-send`。
6. 运行 `beta-callback-probe`，确认公网 `/healthz` 和 `/webhook` challenge 都可用。
7. 在飞书开放平台配置 event subscription。
8. 在 beta 群发送一次委托。
9. 运行 `collect-beta-evidence`，自动保存 `/healthz` JSON 并生成 `docs/BETA_VALIDATION_REPORT_ZH.md`。
10. 再运行 `application-readiness`。

真实 beta runbook：

```bash
stock-agent-orchestrator beta-live-runbook --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

公网 callback 探测命令：

```bash
stock-agent-orchestrator beta-callback-probe --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

收集证据并生成报告：

```bash
stock-agent-orchestrator collect-beta-evidence --config configs/beta.live.toml --callback-url https://your-public-domain.example --db .runtime/webhook.db --healthz-json .runtime/healthz.json --report-output docs/BETA_VALIDATION_REPORT_ZH.md --commit <commit>
```

真实配置初始化命令：

```bash
stock-agent-orchestrator init-beta-live-config --output configs/beta.live.toml
```

`configs/beta.live.toml` 已被 `.gitignore` 排除，不应提交到 GitHub。

## 验收成功标准

真实 beta 验收至少要证明：

- beta 群 @小C-beta 后能建任务。
- 群里出现任务卡。
- 小智-beta / 小巴-beta 后续跟进能更新同一张任务卡。
- `/healthz` 显示 gateway connected。
- `operation_error_count` 为 0。
- SQLite 中存在对应任务 ID。
- 任务 context 中存在 `task_card_message_id`。
- `docs/BETA_VALIDATION_REPORT_ZH.md` 已生成并提交。
