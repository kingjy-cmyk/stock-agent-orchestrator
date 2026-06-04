# 飞书 Beta Live Readiness Bundle

`beta-live-readiness-bundle` 是真实 beta 群验证前的总检查入口。

它会聚合：

- `application-readiness`
- `beta-live-prep-dry-run`
- `beta-live-config-status`
- `beta-live-preflight`
- `beta-live-runbook`
- `beta-live-launch-packet`

## 使用方式

```bash
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

如果真实配置还没填，它不会因为缺配置而崩溃，而是输出 `stage: fill_real_beta_config` 和下一步。

如果真实配置、preflight、runbook、launch packet 都通过，但还没有真实 beta 验证报告，输出：

```text
stage: ready_for_real_beta_group_validation
```

这表示可以进入临时 beta 群验证，但还不能声称申请材料完整。

## 输出含义

- `dry_run_ok`：本地准备链路可跑通。
- `config_ready`：真实配置存在、已被 `.gitignore` 保护、必填字段已填。
- `preflight_ok`：真实 beta 静态准入通过。
- `runbook_ready`：真实 beta runbook 允许启动。
- `launch_ready`：真实 beta 启动包允许进入飞书群验证。
- `missing_real_beta_evidence`：还没有 `docs/BETA_VALIDATION_REPORT_ZH.md`。

## 安全边界

- 不启动 webhook。
- 不发送飞书消息。
- 不写真实配置。
- 不输出 `app_secret`、`verification_token`、`encrypt_key`。

## 进入真实 beta 的条件

至少需要：

- `dry_run_ok=true`
- `config_ready=true`
- `preflight_ok=true`
- `runbook_ready=true`
- `launch_ready=true`
- `stage=ready_for_real_beta_group_validation`

之后再启动 `run-webhook --allow-live-send`，运行 `beta-callback-probe`，配置飞书事件订阅，并在 beta 群里执行首轮消息测试。
