# Performance Optimization

## Model Selection Strategy

**Sonnet (Sonnet 5 / 4.6)** (default main loop):
- Routine implementation, investigation, answers, delegation — the default for almost all work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Haiku 4.5** (fast & cheap):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Opus 4.8** (escalation only — see `rules/role-separation.md` for the 5 trigger conditions):
- Complex architectural decisions
- Research and analysis tasks

**Fable 5 (Mythos-class, above Opus)** (further escalation — use sparingly, only when the problem is indivisible, needs a single full context, and requires maximum depth):
- Hardest cross-cutting analysis that must fit one context (e.g. knowledge-base consolidation, system-wide design review)
- Maximum-effort reasoning sessions

**Role separation:** Sonnet/Haiku is the default execution layer; the thinking tier (Fable 5 / Opus) is escalation-only for the trigger conditions in `rules/role-separation.md`. The automatic enforcement via `hooks/main-loop-execution-guard.py` blocks the thinking tier from executing whenever it's active, regardless of why (guard scope: ADR-020, framing: ADR-024).

## Effort Tiering

- **Main chat** (interactive conversation, global `/effort`): default **high**; raise to **xhigh/max** only for the heavy Opus/Fable escalation work itself, not for routine Sonnet turns.
- **Subagents**: effort is set per-agent via frontmatter `effort:` (implementation lives in the engineering foundation, not here) — **xhigh** for judgment-heavy agents, **high** for review, **medium–high** for execution, **low** for doc-only work, **max** for a Fable-equivalent agent.
- Per-agent `model:`/`effort:` is natively supported via frontmatter; a hook cannot override it — don't try to enforce effort tiering through `main-loop-execution-guard.py`.
