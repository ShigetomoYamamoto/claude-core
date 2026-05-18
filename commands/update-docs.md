---
description: Sync documentation from source-of-truth (package.json, .env.example). Invokes doc-updater agent to update READMEs and guides.
---

# Update Docs

Invokes the **doc-updater** agent to refresh documentation from code.

## What This Command Does

- Reads `package.json` scripts and generates reference tables
- Reads `.env.example` and documents all environment variables
- Updates `docs/CONTRIB.md` and `docs/RUNBOOK.md`
- Flags documentation not modified in 90+ days for review

## When to Use

- After adding new npm scripts or environment variables
- When setup instructions become outdated
- Before releasing a new version

## Related Agents

Invokes `doc-updater` agent at `~/.claude/agents/doc-updater.md`
