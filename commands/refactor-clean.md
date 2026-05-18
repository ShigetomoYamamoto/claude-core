---
description: Safely identify and remove dead code, unused dependencies, and duplicates. Invokes refactor-cleaner agent with analysis tools (knip, depcheck, ts-prune).
---

# Refactor Clean

Invokes the **refactor-cleaner** agent to identify and safely remove dead code.

## What This Command Does

- Runs knip, depcheck, ts-prune to detect unused code
- Categorizes findings by risk: SAFE / CAUTION / DANGER
- Removes only verifiably unused code
- Runs tests after each removal batch
- Documents all deletions

## When to Use

- Codebase has accumulated unused exports or dependencies
- Before a major refactor to reduce surface area
- Periodic cleanup to keep the codebase lean

## Related Agents

Invokes `refactor-cleaner` agent at `~/.claude/agents/refactor-cleaner.md`
