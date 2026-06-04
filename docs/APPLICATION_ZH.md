# Codex 官方活动申请材料草案

## 项目一句话

`stock-agent-orchestrator` 是一个以飞书群为透明控制面的多 agent 股票研究编排系统，用任务 owner、状态机和安全接入层，把一次性聊天委托变成可追踪、可复盘、可审批的研究闭环。

## 解决的问题

普通 agent demo 往往停在一轮对话：

- 用户说完需求后，后续是否推进不可见。
- 多个 agent 之间职责不清。
- 缺证据、缺审批、缺复盘。
- 任务做着做着没有下文。

本项目把核心约束改成：

```text
委托必须持续推进，直到关闭，或者明确等待用户审批。
```

## 为什么适合 Codex

这个项目不是单纯用 Codex 写一个脚本，而是把 Codex 作为长期工程推进者：

- 拆阶段推进仓库能力。
- 参考现有 Codex 飞书通道连接器，对标 Gateway / Operation / Ingress / Worker 模式。
- 把用户的真实协作需求转成代码、配置、测试和文档。
- 每个阶段提交到 GitHub，并保留验证命令。

## 当前已完成

- 原创开源仓库，MIT License。
- Python CLI 工具和可安装包。
- 任务状态机：`小C / 小智 / 小巴` 三角色。
- 飞书风格消息解析。
- Shadow replay 离线回放。
- Fake Feishu beta smoke。
- Local webhook HTTP service。
- Live Feishu client 安全骨架。
- Gateway / Operation / Ingress Queue / Worker 分层。
- `send_allowlist`、`verification_token`、去重、状态健康检查、operation error 记录。
- `beta-live-handoff` 真实 beta 交接单，列出用户审批点、字段收集范围、secret 边界和 final gate 前命令顺序。
- `beta-live-intake-checklist` 真实 beta 配置采集清单，标明字段来源、环境变量、敏感性和停止条件。
- `beta-live-config-from-env` 可从环境变量生成 ignored 的真实 beta 配置。
- `beta-live-config-status` 本地真实配置状态检查，输出脱敏字段状态。
- `beta-live-config-review` 真实 beta 配置安全审阅，确认配置被忽略、字段完整、敏感字段脱敏后再进入 readiness bundle。
- `beta-live-prep-dry-run` 本地验证 beta live 准备链路，不触达真实飞书。
- `beta-live-preflight` 真实 beta 前准入检查。
- `beta-callback-deploy-plan` 公网 callback 部署预案，输出本地监听、公网 URL、飞书开放平台填写项、探测命令和停止条件。
- `beta-validation-guide` 真实 beta 验收向导。
- `beta-live-runbook` 真实 beta 群运行手册。
- `beta-live-launch-packet` 真实 beta 群启动包，输出飞书开放平台填写项、测试消息和证据清单。
- `beta-live-message-script` 真实 beta 群首轮消息脚本，输出 BOOS/小智-beta/小巴-beta 的消息、预期任务卡行为和失败判据。
- `beta-live-readiness-bundle` 真实 beta 前总检查包，聚合 dry-run、配置、preflight、runbook、启动包和证据缺口。
- `beta-live-final-gate` 真实 beta 最终准入门，聚合配置审阅、总检查包、callback 部署预案和消息脚本，输出 go/no-go。
- `beta-live-evidence-rehearsal` 本地彩排真实 beta 证据收集链路，不触达真实飞书，不能作为申请证据。
- `beta-callback-probe` 公网 callback 探测。
- 小智-beta / 小巴-beta 后续消息更新同一任务的 MVP。
- agent 后续消息可通过显式 `BETA-0001` 绑定目标任务。
- 任务 context 已保存任务卡 `message_id`，后续进展优先更新同一张 interactive card。
- 中文说明、安装、维护、路线图、飞书连接器文档。
- 单元测试 127 项通过。

## 当前边界

还没有完成真实飞书 beta 群验证。

当前仓库可以证明：

- 本地安装可用。
- CLI 可运行。
- fake 飞书链路能从委托生成任务卡。
- webhook 可接收飞书风格 payload。
- live 配置有安全准入门。

当前还不能证明：

- 真实飞书 beta 群中能稳定出现任务卡。
- 小智-beta / 小巴-beta 回复能在真实 beta 群中稳定更新同一任务卡。
- reply/thread/message_id 能精准绑定原任务卡。
- 公网 callback 部署、飞书事件订阅和截图证据齐全。

## 申请前建议补齐

优先级最高：

- 真实 beta 群跑通 `@小C-beta -> BETA-0001 任务卡`。
- 补一张 beta 群截图或一段 GIF。
- 补一份 `BETA_VALIDATION_REPORT_ZH.md`，记录日期、配置、步骤、结果、截图。

优先级次高：

- reply/thread/message_id 精准绑定。
- 更细 per-agent/per-chat 限流。
- 简短英文版项目摘要。

## 当前完成度检查

运行：

```bash
stock-agent-orchestrator application-readiness --format markdown
```

当前如果尚未生成真实 beta 验证报告，预期会停在 `80+` 档。

进入 `90+` 档需要：

- `docs/BETA_VALIDATION_REPORT_ZH.md`
- beta 群任务卡截图或 GIF
- `/healthz` 正常证据

## 可展示命令

```bash
python -m pip install -e .
stock-agent-orchestrator doctor
stock-agent-orchestrator demo
stock-agent-orchestrator beta-smoke --config configs/beta.example.toml
stock-agent-orchestrator webhook-smoke --config configs/beta.example.toml
stock-agent-orchestrator beta-live-handoff --shell powershell --callback-url https://your-public-domain.example --task-id BETA-0001 --format markdown
stock-agent-orchestrator beta-live-intake-checklist --shell powershell --format markdown
stock-agent-orchestrator beta-live-prep-dry-run --format markdown
stock-agent-orchestrator init-beta-live-config --output configs/beta.live.toml
stock-agent-orchestrator beta-live-config-from-env --output configs/beta.live.toml --overwrite --format markdown
stock-agent-orchestrator beta-live-config-status --config configs/beta.live.toml --format markdown
stock-agent-orchestrator beta-live-config-review --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-validation-guide --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-live-runbook --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-live-launch-packet --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-live-readiness-bundle --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-callback-deploy-plan --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-live-message-script --task-id BETA-0001 --format markdown
stock-agent-orchestrator beta-live-final-gate --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
stock-agent-orchestrator beta-live-evidence-rehearsal --format markdown
stock-agent-orchestrator beta-live-preflight --config configs/beta.live.toml --callback-url https://your-public-domain.example
stock-agent-orchestrator beta-callback-probe --config configs/beta.live.toml --callback-url https://your-public-domain.example --format markdown
```

## 申请表述草案

我用 Codex 构建了一个开源的多 agent 股票研究编排系统。它以飞书群作为透明控制面，把用户对“小C”的委托拆成可追踪任务，并让“小智 / 小巴”的数据、分析、复盘动作进入同一闭环。项目重点不是预测股票，而是解决多 agent 协作里最常见的“没有下文、责任不清、证据不可见、规则无法沉淀”的问题。

Codex 在这个项目中承担了长期工程 owner 的角色：从需求澄清、架构拆分、连接器对标、配置安全、测试覆盖，到 GitHub 仓库维护和申请材料沉淀，都是按阶段推进并提交的。

当前版本已实现本地可运行 CLI、飞书 webhook MVP、安全 preflight、任务状态机、fake beta 验证、真实 beta 交接单、配置采集清单、配置安全审阅、callback 部署预案、真实 beta 启动包、首轮消息脚本、真实 beta 总检查包、最终准入门、证据收集彩排和完整中文文档。下一步会进入真实飞书 beta 群验证。
