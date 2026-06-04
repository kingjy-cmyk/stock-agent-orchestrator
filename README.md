# Stock Agent Orchestrator

`stock-agent-orchestrator` is a transparent multi-agent stock research backend designed for:

- Feishu group collaboration as the control plane
- task-owner style follow-through instead of one-shot chat replies
- candidate pool screening, seven-layer research cards, and rule-memory updates
- shadow-mode rollout before touching production agents

## Why This Exists

Most agent demos stop after one round of conversation. This project is built around a stricter contract:

`delegated work must keep moving until it is closed or explicitly waiting on the user`

That means:

- every task has a status
- every step has an owner
- missing evidence is visible
- known rules can auto-advance
- unknown rules stop at explicit user review

## Product Shape

- `Feishu group` = control plane
- `task engine` = source of truth
- `beta group` = safe rollout lane
- `web panel` = future observability surface

## Current MVP

The first version in this repository focuses on:

1. task state machine for `小C / 小智 / 小巴`
2. policy boundary between auto-advance and user review
3. adapters for turning Feishu-style messages into task commands
4. bridges to current markdown-based candidate pool and seven-layer artifacts
5. rule-memory suggestions from completed research tasks

## Install

```bash
python -m pip install -e .
```

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

## Rollout Plan

1. shadow mode against the current production Feishu group
2. active testing with `小C-beta / 小智-beta / 小巴-beta`
3. gradual promotion of the new task-owner logic into the current `小C`

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ROLLOUT.md](docs/ROLLOUT.md).
