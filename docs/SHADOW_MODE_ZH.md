# Shadow Mode

## 目的

`Shadow Mode` 的目标是连接飞书消息流，但先保持只读，不主动发言。

离线回放只是进入飞书 Shadow 前的预检手段，不是最终验证。

这样可以先验证三件事：

- 能不能识别你对 `小C` 的正式委托
- 能不能把群内协作还原成任务状态
- 能不能区分 `WAITING_USER` 和静默断链

## 分阶段

### 1. 离线预检

用途：用历史样本或本地 relay 日志检查解析、建任务和断点识别。

限制：用户不能在飞书群里核实流程，所以不算产品验收。

### 2. 飞书只读 Shadow

用途：读取真实飞书群消息流，后台建任务和推断状态。

约束：

- 不主动发言
- 不改正式 agent 配置
- 不接管正在执行的正式任务
- 只生成状态报告和断点报告

### 3. 飞书 beta 主动测试

用途：在测试群里让 beta 三角色主动协同，用户在群里核实完整流程。

约束：

- 只能在 beta 群主动发言
- 正式群仍不受影响
- 新规则和越界动作必须等待用户审批

## 输入格式

支持 `.jsonl`：

```jsonl
{"sender_name": "BOOS", "text": "@小C 研究一下 600809 七层数据"}
{"sender_name": "小智", "text": "七层数据已补齐"}
{"sender_name": "小巴", "text": "分析完成，但需要确认是否新增规则"}
```

也支持普通文本：

```text
BOOS: @小C 今天先给我一份候选池
小C: 已建任务
小巴: 候选池已完成
```

## 运行方式

先从本地 relay 日志生成脱敏样本：

```bash
stock-agent-orchestrator extract-relay-log --log-file C:/Users/Jy95/.local/share/codex-remote/logs/codex-remote-relayd.log --output .runtime/shadow-sample.jsonl --limit 120
```

再执行离线回放：

```bash
stock-agent-orchestrator shadow-replay --input samples/messages.jsonl --format markdown --report .runtime/shadow-report.md
```

输出内容包括：

- 导入了多少条消息
- 创建了多少个任务
- 推进了多少个事件
- 每个任务当前状态
- 发现了哪些断点

## 脱敏规则

日志提取器会把原始 `open_id / chat_id / message_id` 从输出样本中移除，只保留：

- `sender_name`
- `text`
- `created_at`
- `mentions_owner`

当前内置角色映射：

- BOOS
- 小C
- 小智
- 小巴
- 用户

## 断点类型

- `waiting_user`：任务明确停在用户审批，属于正常等待
- `silent_break`：任务停在中间状态，当前责任人明确，但没有继续推进
- `missing_evidence`：任务已收口，但没有挂接证据产物

## 验收标准

Phase 1A 的验收标准是：

- 能导入真实或半真实历史消息样本
- 能自动创建任务
- 能生成状态报告
- 能指出“为什么没下文”
- 全程不影响正式群

最终产品验收必须进入飞书 beta 群：

- 用户能在群里看到任务卡和状态推进
- 小C-beta 能持续追办到落地或等待审批
- 小智-beta / 小巴-beta 的输出能被挂为证据
- 用户能在群里核实整个透明流程
