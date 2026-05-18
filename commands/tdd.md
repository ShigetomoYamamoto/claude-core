---
description: Enforce test-driven development workflow. Scaffold interfaces, generate tests FIRST, then implement minimal code to pass. Ensure 80%+ coverage.
---

# TDD Command

Invokes the **tdd-guide** agent to enforce test-driven development methodology.

## What This Command Does

1. **Scaffold Interfaces** - Define types/interfaces first
2. **Generate Tests First** - Write failing tests (RED)
3. **Implement Minimal Code** - Write just enough to pass (GREEN)
4. **Refactor** - Improve code while keeping tests green (REFACTOR)
5. **Verify Coverage** - Ensure 80%+ test coverage

## TDD Cycle

```
RED → GREEN → REFACTOR → REPEAT
```

**Mandatory**: Tests must be written BEFORE implementation. Never skip the RED phase.

## When to Use

- Implementing new features
- Fixing bugs (write a test that reproduces the bug first)
- Refactoring existing code
- Building critical business logic

## Coverage Requirements

- 80% minimum for all code
- 100% required for financial calculations, auth logic, security-critical code

## Related Agents

Invokes `tdd-guide` agent at `~/.claude/agents/tdd-guide.md`
