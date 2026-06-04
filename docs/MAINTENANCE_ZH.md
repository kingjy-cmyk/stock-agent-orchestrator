# 维护与审批手册

## 你现在最关心的事

你要的不是一次性把仓库写完，而是：

`让我一步步引导你，持续拿到你的审批和建议，把仓库一点点做到成熟。`

这个文档就是后续迭代的执行手册。

## 维护总节奏

建议固定按下面节奏推进：

### 阶段 A：先做最小闭环

先把这三项做稳：

1. 每日候选池
2. 单票七层研究卡
3. 规则建议生成

### 阶段 B：接现有体系但不打扰正式群

- 接正式群做 `shadow mode`
- 只观察，不主动说话
- 只记录任务、状态、断点

### 阶段 C：beta 主动测试

- 建 `小C-beta / 小智-beta / 小巴-beta`
- 在测试群里跑主动推进和催办

### 阶段 D：灰度进正式组

- 先只升级正式 `小C`
- 不先重写正式 `小智 / 小巴`

## 每轮迭代怎么走

每一轮建议都按同一个格式推进：

### Step 1：明确本轮目标

只做一个主题。

例如：

- 接正式群影子模式
- 接七层研究报告自动导入
- 增加规则建议落盘

### Step 2：先给你方案

我先给你：

- 这轮要改什么
- 为什么先做这个
- 风险在哪里
- 哪些点需要你拍板

### Step 3：拿你审批

只有下面两种情况我才自动推进：

- 在你已经明确批准过的规则范围内
- 不涉及新边界、新权限、新风险

### Step 4：落代码和文档

我会同时更新：

- 代码
- README 或中文文档
- 必要测试

### Step 5：本地验证

每轮都至少做：

- 命令可跑
- 测试通过
- 关键路径验证

### Step 6：你验收

你只需要确认三件事：

- 功能是否符合预期
- 文案和角色口径是否对
- 是否进入下一轮

## 什么情况下必须等你审批

以下事项必须先问你：

- 新规则正式生效
- 自动推进边界扩大
- 改动正式群行为
- 接近真实交易
- 付费功能设计
- 用户可见角色或职责重写

## 什么情况下可以直接推进

以下事项我可以在当前规则下直接做：

- 文档补全
- 测试补全
- CLI 或后台骨架完善
- 影子模式的只读接入
- 已明确规则内的状态机推进逻辑

## 维护步骤

### 日常开发

```bash
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
```

### 常用命令

```bash
stock-agent-orchestrator init-db
stock-agent-orchestrator new-task --title "06-05 daily candidate pool" --intent daily_candidate_pool
stock-agent-orchestrator show-task --task-id TASK-0001
stock-agent-orchestrator advance-task --task-id TASK-0001 --actor xiaozhi --message "seven-layer ready"
stock-agent-orchestrator resume-task --task-id TASK-0001 --message "approved"
stock-agent-orchestrator suggest-rules --task-id TASK-0001
```

### 推送前检查

每次提交前至少检查：

1. 测试是否通过
2. README 中文入口是否仍然正确
3. 新增功能是否写进对应文档
4. 是否误带本地数据库或临时文件

## 我后续会怎么引导你

从现在开始，我建议按下面顺序一轮一轮推进：

1. `Phase 1`
   目标：补 `shadow mode` 数据模型和只读 Feishu 适配层
   需要你审批：是否沿用当前正式群 chat_id 和 open_id 配置口径

2. `Phase 2`
   目标：把当前 Hermes 七层报告自动导入为系统任务产物
   需要你审批：最终研究卡展示格式

3. `Phase 3`
   目标：把候选池和七层任务串起来，形成完整日常研究闭环
   需要你审批：什么时点算真正 `CLOSED`

4. `Phase 4`
   目标：beta 群主动测试
   需要你审批：是否创建 beta 版三角色

5. `Phase 5`
   目标：灰度升级正式 `小C`
   需要你审批：正式群允许哪些自动催办行为

## 当前建议的下一步

下一轮最合理的是：

`先做 shadow mode`

因为这是风险最低、价值最高的一步：

- 不打扰现有正式协同
- 能真实观察“为什么会没下文”
- 能为后续 beta 版提供真实任务样本

