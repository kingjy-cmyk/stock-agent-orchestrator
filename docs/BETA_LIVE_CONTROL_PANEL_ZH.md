# 飞书 Beta Live Control Panel

`beta-live-control-panel` 是真实飞书 beta 验证前的一条命令总控台。

它不会联网，不会启动 webhook，不会读取 secret，不会写真实配置，也不会发送飞书消息。它只聚合当前仓库状态，并告诉你下一步该做什么。

它会汇总：

- application readiness 分数。
- beta handoff 交接单。
- beta config review。
- beta readiness bundle。
- beta final gate。
- `docs/BETA_VALIDATION_REPORT_ZH.md` 是否存在。

## 使用

```bash
stock-agent-orchestrator beta-live-control-panel --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

## 输出怎么读

- `stage=collect_or_fix_real_beta_config`：先准备真实 beta 群、飞书 app、open_id、callback 和 ignored 配置。
- `stage=fix_beta_readiness_bundle`：配置已接近可用，但 readiness bundle 还有前置检查没过。
- `stage=fix_beta_final_gate`：总检查通过不完整，先修 final gate。
- `stage=ready_to_start_real_beta_execution`：本地门禁允许进入真实 beta 执行，但仍需要临时 beta 群实测。
- `stage=real_beta_evidence_present`：真实 beta 报告已存在，重新跑 `application-readiness`。

## 关键边界

`beta-live-control-panel` 通过不等于申请已完成。

申请完成仍必须有：

- 临时 beta 群真实消息流。
- 任务卡截图或录屏。
- `/healthz` 正常证据。
- `collect-beta-evidence` 生成的 `docs/BETA_VALIDATION_REPORT_ZH.md`。

## 推荐顺序

先运行总控台：

```bash
stock-agent-orchestrator beta-live-control-panel --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
```

如果 stage 允许真实 beta 执行，再按输出的 `Commands` 顺序启动 webhook、探测 callback、发送 beta 消息、收集证据。

## 停止条件

- `stage` 不是 `ready_to_start_real_beta_execution` 时不要启动 `--allow-live-send`。
- 目标群不是临时 beta 群时停止。
- 任何 secret 出现在公开输出、GitHub 或群聊时停止并轮换。
- `/healthz` 出现 `operation_error_count > 0` 时停止。
