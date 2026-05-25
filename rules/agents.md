# Agent Orchestration

## Pre-Implementation Branch Check (MANDATORY)

Before writing or editing any code file, always verify the current branch:

1. Run `git branch --show-current`
2. If the result is `main`, `master`, or `develop` — **STOP immediately**
   - Do NOT proceed with any file changes
   - Tell the user: "現在 protected branch にいます。作業ブランチを作成してから実装を開始します。"
   - Run `/create-branch` (or `git checkout -b <prefix>/<summary>_YYYYMMDD` if develop is unavailable)
   - Resume implementation only after confirming the new branch

This check applies to ALL agents that write or edit files.

---

## Proactive Agent Invocation

These agents MUST be invoked automatically — without waiting for the user to ask:

| Trigger | Agent to invoke |
|---------|----------------|
| User provides a free-form goal / new feature idea (full-auto mode start) | **requirements-analyst** — structure requirements before design |
| User provides a specific task / GitHub Issue / bug report (support mode start) | **task-analyst** — break down into implementable units before planning |
| New project, or feature requires new DB schema / API contract / tech stack decision | **architect** — requirements definition → design → ADR before anything else |
| Implementing a feature within an existing, defined design | **planner** — implementation plan before writing code |
| Fixing a bug or implementing a new feature | **tdd-guide** — enforce tests-first |
| Any code has been written or modified | **code-reviewer** — review immediately after |
| Code touches auth, user input, secrets, or API endpoints | **security-reviewer** — review before committing (in addition to code-reviewer) |
| Build or type errors occur | **build-error-resolver** — fix before continuing |
| DB schema migrations pending or about to deploy | **migration-runner** — apply migrations safely |
| Ready to deploy after PR merge | **deploy-runner** — deploy + verify + auto-rollback on failure |
| Manual rollback needed after a previous deploy | **rollback-runner** — revert to a previous version |
| PR has reviewer comments that need addressing | **review-responder** — implement requested changes and reply |

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth.ts
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utils.ts

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker
