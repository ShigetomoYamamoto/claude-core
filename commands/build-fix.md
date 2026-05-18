---
description: Fix TypeScript and build errors incrementally. Invokes build-error-resolver agent for minimal-diff fixes without architectural changes.
---

# Build Fix

Invokes the **build-error-resolver** agent to fix TypeScript, compilation, and build errors.

## What This Command Does

- Runs `tsc --noEmit` or `npm run build` to collect all errors
- Fixes errors one at a time with minimal diffs
- Re-runs build after each fix to verify
- Stops if a fix introduces new errors or same error persists after 3 attempts
- Reports errors fixed / remaining

## When to Use

- `npm run build` fails
- `npx tsc --noEmit` shows type errors
- Import/module resolution errors
- Dependency version conflicts

## Related Agents

Invokes `build-error-resolver` agent at `~/.claude/agents/build-error-resolver.md`
