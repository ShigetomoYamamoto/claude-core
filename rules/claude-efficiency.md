# Performance Optimization

## Model Selection Strategy

**Opus 5** (default main loop — see `rules/role-separation.md`, [ADR-029](../docs/adr/029-opus-default-main-loop.md)):
- The main loop cannot execute (guard: ADR-026), so it judges, decomposes, delegates and verifies — frontier judgment belongs in that seat
- Complex architectural decisions, research and analysis
- Orchestrating multi-agent workflows

**Sonnet (Sonnet 5 / 4.6)** (default execution layer):
- All actual execution: implementation, edits, git, tests, tool-driving — delegated from the main loop
- Investigation and answers that need no frontier judgment
- Complex coding tasks

**Haiku 4.5** (fast & cheap):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Fable 5 (Mythos-class, above Opus)** (escalation from Opus — use sparingly, only when the problem is indivisible, needs a single full context, and requires maximum depth):
- Hardest cross-cutting analysis that must fit one context (e.g. knowledge-base consolidation, system-wide design review)
- Maximum-effort reasoning sessions

**Role separation:** Opus is the default main loop; Sonnet/Haiku is the default execution layer; Fable is escalation-only for the conditions in `rules/role-separation.md`. Enforcement is a separate axis: `hooks/main-loop-execution-guard.py` blocks the **main loop** — on every model, whatever it is running — from editing and from state-changing Bash, so execution is delegated to a subagent (axis: ADR-026, naming: ADR-027, current default: ADR-029).

## Effort Tiering

- **Main chat** (interactive conversation, global `/effort`): the main loop runs on Opus by default, so **high** covers routine orchestration (read, judge, delegate, verify) — Anthropic's own guidance starts Opus 5 and Fable 5.1 at the default `high` (`xhigh` is the recommendation for Opus 4.8/4.7, not Opus 5). Raise to **xhigh/max** only for judgment work that actually needs the depth — architecture/foundational calls, Fable-bar cases — not for every Opus turn.
- **Subagents**: effort is set per-agent via frontmatter `effort:` (implementation lives in the engineering foundation, not here) — **xhigh** for judgment-heavy agents, **high** for review, **medium–high** for execution, **low** for doc-only work, **max** for a Fable-equivalent agent.
- Per-agent `model:`/`effort:` is natively supported via frontmatter; a hook cannot override it — don't try to enforce effort tiering through `main-loop-execution-guard.py`.
