# Memory — Outer-Loop Learning

Inner-loop feedback (hooks, reviewers, tests) catches mistakes within a single run.
The outer loop is what makes the *next* run start smarter. Agents forget between
sessions; the repository does not. Write durable lessons down so they survive context
resets.

> **Mechanism = official auto-memory.** Claude Code now ships a built-in memory system:
> it stores one fact per file under the project's `memory/` dir with frontmatter,
> keeps a `MEMORY.md` index, auto-loads it at session start, and recalls relevant
> entries. **Do not hand-roll the file format, index, or recall** — the official
> system already specifies and runs it (its instructions are injected each session).
> This rule covers only the *judgment* the official prompt does not: **what** is worth
> persisting and **when** to write it in an autonomous loop.

## What to write

Persist a memory when something would otherwise have to be re-learned:

- A review finding you hit more than once (the same class of bug / smell).
- A non-obvious constraint or gotcha not derivable from the code or git history.
- A recovery: a failure and the fix that worked, so the next run skips the dead end.
- A user correction on *how to work* (preference, workflow), with the reason why.

## What NOT to write

- Anything already recorded in code, tests, ADRs, CLAUDE.md, or git history.
- One-off details that only mattered to a single conversation.
- Secrets or credentials — never (see `rules/security.md`).

If asked to remember something the repo already records, capture only what was
*non-obvious* about it.

## How to write

Follow the official auto-memory format (the session prompt is authoritative). The
points that still matter for *our* workflow:

- Before saving, check for an existing file that covers it — update rather than duplicate.
- Delete memories that turn out to be wrong.
- Convert relative dates to absolute ("today" -> the actual date).

## When to write (in a loop)

- At the end of an autonomous run, before reporting: record what the next run should know.
- When the same reviewer finding appears a second time — promote it to a memory so the
  loop stops re-introducing it.

## Relation to other rules

- `rules/loop-safety.md` — the run itself (inner loop + hard stops).
- `rules/parallel-worktree.md` — isolating concurrent writers.
- This file — carrying lessons *across* runs (the outer loop).
