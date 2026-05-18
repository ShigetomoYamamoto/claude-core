---
description: Comprehensive security and quality review of uncommitted changes. Invokes code-reviewer agent to check for vulnerabilities, code quality issues, and best practice violations.
---

# Code Review

Invokes the **code-reviewer** agent to review all uncommitted changes.

## What This Command Does

- Gets changed files via `git diff --name-only HEAD`
- Checks for security issues (hardcoded secrets, SQL injection, XSS)
- Reviews code quality (large functions, deep nesting, missing error handling)
- Reports findings by priority: CRITICAL / HIGH / MEDIUM

## When to Use

- Before committing or opening a PR
- After implementing a new feature
- When explicit review is needed beyond auto-invocation

## Related Agents

Invokes `code-reviewer` agent at `~/.claude/agents/code-reviewer.md`
