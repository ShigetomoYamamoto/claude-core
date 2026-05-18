---
description: Generate and run end-to-end tests with Playwright. Invokes e2e-runner agent to discover project-specific scenarios, create test journeys, run tests, and capture artifacts.
---

# E2E Command

Invokes the **e2e-runner** agent to generate, maintain, and execute end-to-end tests.

## What This Command Does

1. **Scenario Discovery** - Reads `.claude/e2e-scenarios.md` for project-specific critical flows. Generates the file by scanning the project if it does not exist.
2. **Test Generation** - Creates Playwright tests using Page Object Model pattern
3. **Test Execution** - Runs tests across browsers
4. **Artifact Capture** - Screenshots, videos, traces on failures
5. **Flaky Test Management** - Identifies and quarantines unstable tests

## When to Use

- Before merging a PR to verify critical flows
- After implementing a new user-facing feature
- Setting up an E2E test suite for a project for the first time

## Project-Specific Scenarios

Project-specific test scenarios are stored in `.claude/e2e-scenarios.md` at the repo root.
The e2e-runner agent generates this file automatically on first run by scanning routes,
components, and API endpoints. Edit the file to refine priorities.

## Related Agents

Invokes `e2e-runner` agent at `~/.claude/agents/e2e-runner.md`
