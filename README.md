# Stock Agent Orchestrator

`stock-agent-orchestrator` is a transparent multi-agent stock research backend designed for:

- Feishu group collaboration as the control plane
- task-owner style follow-through instead of one-shot chat replies
- candidate pool screening, seven-layer research cards, and rule-memory updates
- shadow-mode rollout before touching production agents

## 中文说明

这是一个面向 `小C / 小智 / 小巴` 协同体系的后台任务编排仓库。

它的目标不是再做一个“一问一答”的聊天机器人，而是做一个：

- 你把事情委托给 `小C` 后，系统会持续跟进到闭环
- 过程透明，仍然以 `飞书群` 作为控制面
- 能跑通 `每日候选池 -> 单票七层研究 -> 规则复盘更新`
- 前期先做 `研究 + 模拟盘`
- 后期再逐步演进到更成熟的自动化研究与付费能力

中文文档入口：

- [申请材料草案](docs/APPLICATION_ZH.md)
- [申请完成度检查](docs/APPLICATION_READINESS_ZH.md)
- [演示脚本](docs/DEMO_SCRIPT_ZH.md)
- [飞书 Beta 验收向导](docs/BETA_VALIDATION_GUIDE_ZH.md)
- [飞书 Beta Live Runbook](docs/BETA_LIVE_RUNBOOK_ZH.md)
- [飞书 Beta 验证报告模板](docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md)
- [中文产品介绍](docs/INTRO_ZH.md)
- [飞书优先原则](docs/FEISHU_FIRST_ZH.md)
- [飞书连接器架构](docs/FEISHU_CONNECTOR_ZH.md)
- [Codex 飞书通道对标矩阵](docs/CODEX_FEISHU_PARITY_ZH.md)
- [长线推进任务](docs/LONG_RUNNING_TASK_ZH.md)
- [运行前提与最小配置](docs/PREREQUISITES_ZH.md)
- [中文安装与快速验证](docs/INSTALL_ZH.md)
- [中文流程与最终目标](docs/WORKFLOW_ZH.md)
- [中文维护与审批手册](docs/MAINTENANCE_ZH.md)
- [中文迭代路线图](docs/ROADMAP_ZH.md)

## Why This Exists

Most agent demos stop after one round of conversation. This project is built around a stricter contract:

`delegated work must keep moving until it is closed or explicitly waiting on the user`

That means:

- every task has a status
- every step has an owner
- missing evidence is visible
- known rules can auto-advance
- unknown rules stop at explicit user review

## Application Readiness

This repository is being prepared as an open-source Codex-built project.

Current status:

- local install/demo/smoke paths are documented
- Feishu connector has a safe beta preflight gate
- 83 unit tests pass locally
- real Feishu beta validation is still pending

Current readiness can be checked by command:

```bash
stock-agent-orchestrator application-readiness --format markdown
```

For the application narrative and demo checklist, see:

- [申请材料草案](docs/APPLICATION_ZH.md)
- [申请完成度检查](docs/APPLICATION_READINESS_ZH.md)
- [演示脚本](docs/DEMO_SCRIPT_ZH.md)
- [飞书 Beta 验收向导](docs/BETA_VALIDATION_GUIDE_ZH.md)
- [飞书 Beta Live Runbook](docs/BETA_LIVE_RUNBOOK_ZH.md)
- [飞书 Beta 验证报告模板](docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md)

## Product Shape

- `Feishu group` = control plane
- `task engine` = source of truth
- `beta group` = safe rollout lane
- `web panel` = future observability surface

Minimum full workflow requirement:

- 1 user approver
- 3 visible agents: `小C`, `小智`, `小巴`
- 1 Feishu group as the transparent control plane
- 1 orchestrator backend with persistent task storage

See [运行前提与最小配置](docs/PREREQUISITES_ZH.md).

## Current MVP

The first version in this repository focuses on:

1. task state machine for `小C / 小智 / 小巴`
2. policy boundary between auto-advance and user review
3. adapters for turning Feishu-style messages into task commands
4. bridges to current markdown-based candidate pool and seven-layer artifacts
5. rule-memory suggestions from completed research tasks

## Chinese MVP Summary

当前首版已经落地的内容：

1. 任务状态机：`NEW -> PLANNED -> SCANNING -> ENRICHING -> ANALYZING -> FOLLOWING_UP -> RECORDED -> CLOSED`
2. 审批边界：已知规则内可自动推进；新规则或越界事项进入 `WAITING_USER`
3. 现有体系桥接：可以读取当前 `candidate_list.md` 和七层研究报告
4. CLI：支持建库、建任务、推进任务、恢复任务、查看任务、候选池导入、离线影子回放、规则建议生成
5. 测试：当前核心单元测试已通过

下一阶段不是“重做三个人”，而是：

- 先接正式群做 `shadow mode`
- 再建 `小C-beta / 小智-beta / 小巴-beta`
- 最后灰度升级现在的 `小C`

## Install

```bash
python -m pip install -e .
```

Bootstrap on a fresh machine:

```powershell
.\scripts\bootstrap.ps1
```

macOS / Linux:

```bash
sh scripts/bootstrap.sh
```

Quick environment check:

```bash
stock-agent-orchestrator doctor
```

Run a bundled local demo as an installation preflight only:

```bash
stock-agent-orchestrator demo
```

Product validation must happen through Feishu. Local demo proves the package can run; it does not prove the transparent multi-agent workflow is usable.

## CLI

Initialize a local task database:

```bash
stock-agent-orchestrator init-db
```

Create a task:

```bash
stock-agent-orchestrator new-task --title "06-05 daily candidate pool" --intent daily_candidate_pool
```

Show a task:

```bash
stock-agent-orchestrator show-task --task-id TASK-0001
```

Advance a task manually during beta testing:

```bash
stock-agent-orchestrator advance-task --task-id TASK-0001 --actor xiaozhi --message "seven-layer ready"
```

Resume a task after user review:

```bash
stock-agent-orchestrator resume-task --task-id TASK-0001 --message "approved"
```

Generate rule-memory suggestions from a completed research task:

```bash
stock-agent-orchestrator suggest-rules --task-id TASK-0001
```

Preview the current candidate pool from the existing OpenClaw markdown output:

```bash
stock-agent-orchestrator ingest-candidates --candidate-file /path/to/candidate_list.md
```

Replay offline Feishu-style message samples without touching the production group:

```bash
stock-agent-orchestrator shadow-replay --input /path/to/messages.jsonl --format markdown --report .runtime/shadow-report.md
```

Extract a sanitized local sample from `codex-remote-relayd.log`:

```bash
stock-agent-orchestrator extract-relay-log --log-file /path/to/codex-remote-relayd.log --output .runtime/shadow-sample.jsonl --limit 120
```

Validate a beta/formal config before Feishu connector work:

```bash
stock-agent-orchestrator validate-config --config configs/beta.example.toml
```

Render the task card that will later be sent into Feishu:

```bash
stock-agent-orchestrator render-task-card --task-id TASK-0001
```

Run a fake beta Feishu connector smoke test without touching a real group:

```bash
stock-agent-orchestrator beta-smoke --config configs/beta.example.toml
```

Run the worker-stage smoke test with queued fake Feishu events:

```bash
stock-agent-orchestrator worker-smoke --config configs/beta.example.toml
```

Run the local Feishu webhook gateway smoke test:

```bash
stock-agent-orchestrator webhook-smoke --config configs/beta.example.toml
```

Run the local webhook HTTP service. This still uses `FakeFeishuClient` and will not send to a real Feishu group:

```bash
stock-agent-orchestrator run-webhook --config configs/beta.example.toml --host 127.0.0.1 --port 8787
```

Live Feishu sending is guarded. It requires `feishu.send_mode = "live"`, real app credentials, and the explicit CLI flag:

```bash
stock-agent-orchestrator run-webhook --config configs/beta.live.example.toml --allow-live-send
```

For beta safety, the live target chat must also be listed in `feishu.send_allowlist`, and `feishu.verification_token` must be configured for Feishu callback token verification. The webhook gateway exposes runtime counters at `/healthz`, including duplicate events and operation errors.

Before touching a real beta group, run the stricter live preflight gate:

```bash
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example
```

Generate the real beta runbook before starting live webhook sending:

```bash
stock-agent-orchestrator beta-live-runbook --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

After a real beta run, collect `/healthz` and generate a validation report:

```bash
stock-agent-orchestrator collect-beta-evidence --config configs/beta.live.toml --callback-url https://your-public-domain.example --db .runtime/webhook.db --task-id BETA-0001 --healthz-json .runtime/healthz.json --report-output docs/BETA_VALIDATION_REPORT_ZH.md
```

Supported sample formats:

- `.jsonl`: one JSON object per line with `sender_name`, `text`, optional `created_at`, optional `mentions_owner`
- plain text: one message per line, preferably `sender: message`

## Rollout Plan

1. local preflight only: install, doctor, demo
2. fake Feishu connector smoke: message event -> task -> task card send request
3. read-only Feishu Shadow Mode: observe messages and build task state without speaking
4. active Feishu beta group with `小C-beta / 小智-beta / 小巴-beta`
5. gradual promotion of the new task-owner logic into the current `小C`

## What To Read Next

- English architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- English rollout: [docs/ROLLOUT.md](docs/ROLLOUT.md)
- 申请材料草案: [docs/APPLICATION_ZH.md](docs/APPLICATION_ZH.md)
- 申请完成度检查: [docs/APPLICATION_READINESS_ZH.md](docs/APPLICATION_READINESS_ZH.md)
- 演示脚本: [docs/DEMO_SCRIPT_ZH.md](docs/DEMO_SCRIPT_ZH.md)
- 飞书 Beta 验证报告模板: [docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md](docs/BETA_VALIDATION_REPORT_TEMPLATE_ZH.md)
- 飞书 Beta Live Runbook: [docs/BETA_LIVE_RUNBOOK_ZH.md](docs/BETA_LIVE_RUNBOOK_ZH.md)
- 飞书优先原则: [docs/FEISHU_FIRST_ZH.md](docs/FEISHU_FIRST_ZH.md)
- 飞书连接器架构: [docs/FEISHU_CONNECTOR_ZH.md](docs/FEISHU_CONNECTOR_ZH.md)
- 飞书 Beta Live Preflight: [docs/BETA_LIVE_PREFLIGHT_ZH.md](docs/BETA_LIVE_PREFLIGHT_ZH.md)
- Codex 飞书通道对标矩阵: [docs/CODEX_FEISHU_PARITY_ZH.md](docs/CODEX_FEISHU_PARITY_ZH.md)
- 长线推进任务: [docs/LONG_RUNNING_TASK_ZH.md](docs/LONG_RUNNING_TASK_ZH.md)
- 运行前提与最小配置: [docs/PREREQUISITES_ZH.md](docs/PREREQUISITES_ZH.md)
- 中文安装/验证: [docs/INSTALL_ZH.md](docs/INSTALL_ZH.md)
- 中文产品说明: [docs/INTRO_ZH.md](docs/INTRO_ZH.md)
- 中文全流程: [docs/WORKFLOW_ZH.md](docs/WORKFLOW_ZH.md)
- 中文维护/审批: [docs/MAINTENANCE_ZH.md](docs/MAINTENANCE_ZH.md)
- 中文路线图: [docs/ROADMAP_ZH.md](docs/ROADMAP_ZH.md)
- 中文 Shadow Mode 说明: [docs/SHADOW_MODE_ZH.md](docs/SHADOW_MODE_ZH.md)
