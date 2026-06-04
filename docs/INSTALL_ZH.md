# 安装与快速验证

## 目标

这个仓库应当做到：换一台新电脑后，能直接安装、做环境自检、跑内置样本，再按需接入本地日志测试。

当前页面只解决“新电脑能不能装起来、能不能跑预检”的问题。

重要边界：这不是产品验收。产品主体必须连接飞书平台，在飞书群里验证透明协同流程。

## 环境要求

- Python 3.11+
- Git
- Windows / macOS / Linux 均可

## 安装

```bash
git clone https://github.com/kingjy-cmyk/stock-agent-orchestrator.git
cd stock-agent-orchestrator
python -m pip install -e .
```

安装会自动拉取 `cryptography`，用于飞书 encrypt payload 解密。

## 新电脑一键启动

Windows PowerShell：

```powershell
.\scripts\bootstrap.ps1
```

macOS / Linux：

```bash
sh scripts/bootstrap.sh
```

脚本会自动完成：

- 创建 `.venv`
- 安装当前仓库
- 运行 `doctor`
- 运行 `demo`

## 一键自检

```bash
stock-agent-orchestrator doctor
```

期望结果：

- `ok` 为 `true`
- Python 版本不低于 3.11
- `.runtime` 目录可创建
- 包可以正常导入

## 一键演示

```bash
stock-agent-orchestrator demo
```

这个命令只是安装预检。

这个命令会：

- 在 `.runtime/` 写入一份内置消息样本
- 建立一个本地 SQLite 数据库
- 跑一次离线 Shadow 回放
- 输出一份 Shadow Report

它不能证明：

- 小C 能在飞书群里持续追办
- 用户能在群里看到状态
- 小智 / 小巴 的协同能被用户核实
- 任务真的形成透明闭环

## 用本机真实日志测试

如果机器上有 `codex-remote-relayd.log`，可以先抽取脱敏样本：

```bash
stock-agent-orchestrator extract-relay-log --log-file C:/Users/Jy95/.local/share/codex-remote/logs/codex-remote-relayd.log --output .runtime/shadow-sample.jsonl --limit 120
```

再回放：

```bash
stock-agent-orchestrator shadow-replay --input .runtime/shadow-sample.jsonl --db .runtime/shadow.db --format markdown --report .runtime/shadow-report.md
```

## 本地文件说明

`.runtime/` 已在 `.gitignore` 中，里面的样本、数据库、报告默认不提交到 GitHub。

## 当前边界

- 安装预检阶段不接正式飞书群
- 当前不发飞书消息
- 当前不做实盘交易
- 当前只验证本地环境、任务识别、状态推进和断点报告

下一阶段必须回到飞书：

- 先只读接入飞书消息流做 Shadow
- 再在 beta 群让小C-beta / 小智-beta / 小巴-beta 主动协同
- 最后灰度升级正式小C
