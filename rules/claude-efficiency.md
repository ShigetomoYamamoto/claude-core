# Performance Optimization

## Model Selection Strategy

**Haiku 4.5** (fast & cheap):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Sonnet (Sonnet 5 / 4.6)** (best coding cost/performance):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Opus 4.8** (deep reasoning):
- Complex architectural decisions
- Research and analysis tasks

**Fable 5 (Mythos-class, above Opus)** (deepest reasoning — use sparingly):
- Hardest cross-cutting analysis that must fit one context (e.g. knowledge-base consolidation, system-wide design review)
- Maximum-effort reasoning sessions

**Role separation:** the thinking tier (Fable 5 / Opus) handles thinking (research, planning, decision-making); Sonnet/Haiku handle execution (editing, deletion, repeated operations). The automatic enforcement via `hooks/opus-execution-guard.py` is defined in `rules/role-separation.md` (guard scope: ADR-020).
