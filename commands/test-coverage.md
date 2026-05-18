---
description: Analyze test coverage and generate missing tests to reach 80%+ threshold. Invokes tdd-guide agent to identify and fill coverage gaps.
---

# Test Coverage

Invokes the **tdd-guide** agent to analyze coverage and generate missing tests.

## What This Command Does

- Runs tests with coverage: `npm test --coverage`
- Identifies files below 80% threshold
- Generates unit, integration, or E2E tests for uncovered paths
- Verifies new tests pass
- Reports before/after coverage metrics

## When to Use

- Coverage has dropped below 80%
- After adding new features without tests
- Before a release to verify coverage targets

## Related Agents

Invokes `tdd-guide` agent at `~/.claude/agents/tdd-guide.md`
