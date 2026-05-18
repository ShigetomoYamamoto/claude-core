---
description: Analyze codebase structure and update architecture codemaps in docs/CODEMAPS/. Invokes doc-updater agent.
---

# Update Codemaps

Invokes the **doc-updater** agent to regenerate architecture codemaps.

## What This Command Does

- Scans source files for imports, exports, and dependencies
- Generates or updates `docs/CODEMAPS/` (frontend, backend, database, integrations)
- Adds freshness timestamps
- Requests approval if changes exceed 30% diff from previous version

## When to Use

- After adding major new modules or restructuring directories
- Before onboarding new team members
- Periodically to keep architecture docs in sync with reality

## Related Agents

Invokes `doc-updater` agent at `~/.claude/agents/doc-updater.md`
