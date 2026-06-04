# Architecture

## Goal

Turn a chat-first multi-agent workflow into a stateful research system that can:

- keep working after a single user delegation
- show where a task is blocked
- auto-advance inside approved rule boundaries
- stop only when user review is genuinely required

## Control Model

### Visible Roles

- `小C`: task owner, closer, memory maintainer
- `小智`: screening, data enrichment, intraday monitoring
- `小巴`: analysis, trade recommendation, rule explanation

### Hidden Runtime Components

- `Orchestrator`: task state machine and routing
- `Risk Engine`: approval boundary and execution policy
- `Memory Engine`: lessons, rule updates, replayable artifacts

## Task Lifecycle

```text
NEW
  -> PLANNED
  -> SCANNING
  -> ENRICHING
  -> ANALYZING
  -> FOLLOWING_UP
  -> RECORDED
  -> CLOSED
```

Optional interruption:

```text
ANY_ACTIVE_STATE -> WAITING_USER -> previous active track
```

## Intent Types

- `daily_candidate_pool`
- `single_stock_research`
- `rule_update`

## Artifacts

- candidate pool snapshots
- seven-layer research cards
- intraday monitor alerts
- rule update suggestions

## Approval Boundary

### Auto-Advance

Allowed when all of the following are true:

- the task stays inside existing rules
- no new execution privilege is requested
- the requested output is research or simulation only

### User Review Required

Triggered when any of the following happens:

- a new rule is proposed
- a rule conflicts with stored policy
- the flow escalates toward real trading or paid automation
- evidence is insufficient to close the task

## Current-System Bridge

The MVP reads from the existing markdown-first workflow:

- OpenClaw `candidate_list.md`
- Hermes seven-layer reports
- Hermes intraday monitor reports

This lets the new engine run in shadow mode before it starts actively steering the production group.

