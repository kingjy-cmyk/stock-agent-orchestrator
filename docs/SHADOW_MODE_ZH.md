# Shadow Mode 离线回放

## 目的

`Shadow Mode` 的第一步不是接入正式飞书群，而是用历史消息样本做离线回放。

这样可以先验证三件事：

- 能不能识别你对 `小C` 的正式委托
- 能不能把群内协作还原成任务状态
- 能不能区分 `WAITING_USER` 和静默断链

## 不会做什么

当前离线回放不会：

- 监听正式群
- 往正式群发消息
- 修改当前 `小C / 小智 / 小巴` 的配置
- 接管任何正在执行的正式任务

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
