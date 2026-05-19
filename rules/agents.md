# Agent Orchestration

## Proactive Agent Invocation

These agents MUST be invoked automatically — without waiting for the user to ask:

| Trigger | Agent to invoke |
|---------|----------------|
| New project, or feature requires new DB schema / API contract / tech stack decision | **architect** — requirements definition → design → ADR before anything else |
| Implementing a feature within an existing, defined design | **planner** — implementation plan before writing code |
| Fixing a bug or implementing a new feature | **tdd-guide** — enforce tests-first |
| Any code has been written or modified | **code-reviewer** — review immediately after |
| Code touches auth, user input, secrets, or API endpoints | **security-reviewer** — review before committing (in addition to code-reviewer) |
| Build or type errors occur | **build-error-resolver** — fix before continuing |

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
