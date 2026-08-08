# Role Separation — Sonnet Default Main Loop, Thinking Tier for Escalation

## The principle

**Default: Sonnet runs the main loop** — routine implementation, investigation, answers,
and delegation. Reserve the thinking tier (Fable 5 / Opus 4.8) for escalation only,
when one of these applies:

- Resolving ambiguous requirements
- Architecture / foundational decisions
- Non-obvious or platform-dependent risk
- Confirming constraints before a destructive/irreversible operation
- Final approval of a significant change

**Fable is a further escalation, not a default alternative to Opus** — reserve it for
problems that are indivisible, must be reviewed as a whole in one context, and need
maximum reasoning depth (e.g. knowledge-base consolidation, system-wide design review).

| | Sonnet (5 / 4.6) — default | Thinking tier (Fable 5 / Opus 4.8) — escalation only | Haiku 4.5 |
|---|---|---|---|
| **Best for** | main-loop execution: implementation, investigation, answers, orchestrating delegation | the 5 escalation triggers above | lightweight agents, worker tasks, frequent calls |

After an escalation resolves the judgment call, hand back to Sonnet for execution —
don't keep running state-changing operations on the escalated model. **Maker ≠
checker** for significant changes: get independent review (a separate Sonnet session,
or Opus) rather than self-certifying — see `rules/safety-irreversible.md`. Model
cost/perf detail and effort tiering live in `rules/claude-efficiency.md` (single
source of truth — this file defines only the role split).

## Enforcement: the opus-execution-guard hook

`hooks/opus-execution-guard.py` ([ADR-016](../docs/adr/016-opus-execution-guard.md),
extended by [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md), reframed by
[ADR-024](../docs/adr/024-sonnet-default-main-loop.md), **axis replaced by
[ADR-026](../docs/adr/026-execution-guard-role-axis.md)**) enforces the split
mechanically. It keys on **role, not model**: the only thing it reads from stdin is
whether `agent_id` is present.

- **Main loop** (no `agent_id`) — cannot run `Edit` / `Write` / `MultiEdit` /
  `NotebookEdit`, nor state-changing Bash (`rm` / `mv` / `cp` / `tee` / `mkdir` /
  `sed -i` / `git add|commit|push|reset|clean` / `npm|pip install` / redirection).
  **This holds on every model, including Sonnet** — that is the point of ADR-026.
- **Execution layer** (stdin carries `agent_id`) — unrestricted. This is where the
  work happens.
- **Two path exceptions for the main loop**: auto-memory
  (`~/.claude/projects/*/memory/`) and the session scratchpad. Nothing else. The
  boundary is fixed absolute paths, never a judgment about whether a file is
  "config" or "product code" — in a config repo like claude-core those are the same
  files (ADR-026).
- **Always allowed**: read-only Bash (`ls`, `cat`, `git status|diff|log`), test /
  lint / typecheck runs, redirection to `/dev/null`, and `Agent` delegation. The
  main loop keeps its eyes so it can verify what the execution layer reports
  (maker ≠ checker, `rules/safety-irreversible.md`).
- **Fail-open** when the decision cannot be made (no path in `tool_input`, malformed
  stdin) — [ADR-006](../docs/adr/006-hook-error-policy.md).

Before ADR-026 the guard read the transcript's latest assistant `message.model` and
fired only on the thinking tier. After ADR-024 made Sonnet the default main loop that
meant it never fired in normal operation, so the role split existed as a norm but not
as a mechanism. The model check and the transcript read are gone.

## Physical-layer scope (do not overstate — aligned with [ADR-014](../docs/adr/014-loop-engineering-as-discipline.md))

The hook fires **only** on Bash and `Edit|Write|MultiEdit|NotebookEdit`. It does **NOT** fire on MCP-routed tool calls (Playwright, repeated MCP ops) or on deploy/migrate/rollback commands. Those are covered by this norm plus the executing agents' `model: sonnet` declaration — never claim the hook guards them.

## Delegating and escalating

1. **Delegate first** — execution work that needs no judgment goes to a Sonnet
   subagent via the `Agent` tool (`model: sonnet`). A subagent declaring
   `model: sonnet` passes the guard's `agent_id` gate regardless of what the main
   loop is running, so this works mid-escalation.
   - **Pass `run_in_background: false`.** Subagents run in the background by
     default (Claude Code 2.1.198+), so a fire-and-forget delegation ends the turn
     and the loop stalls even after the subagent finishes. Wait for the report,
     then continue.
   - **Never ask the user to switch models.** Delegation is something you can do
     yourself, right now; `/model sonnet` is a user action and is not a substitute
     for delegating.
   - Do NOT delegate to the built-in `general-purpose` / `claude` agent while
     escalated: it inherits the parent (thinking-tier) model, so it runs expensive
     and off-role (even though the `agent_id` gate would let it through). Use a
     dedicated `model: sonnet` subagent instead.
   - The concrete engineering execution agents (`git-runner`, `executor`, `fixer`,
     `tdd-guide`, `build-error-resolver`, `e2e-runner`) live in the
     claude-engineering foundation, not here.
2. **Escalate** — switch to the thinking tier only for one of the 5 triggers above:
   `/model opus` (or `/model fable` for the stricter Fable bar).
3. **Return** — once the judgment call is made, resume on Sonnet (`/model sonnet`);
   Sonnet is the default, so this is usually just continuing the main conversation.

## Tool operations

Browser automation and repeated MCP execution belong to Sonnet by default:
- **Design** (how to drive it): Sonnet, unless one of the 5 escalation triggers applies.
- **Execution** (running the steps): Sonnet.

Example: designing a Playwright scenario stays on Sonnet; escalate only if the
scenario surfaces a non-obvious architecture question.

## Related

- `rules/claude-efficiency.md` — model performance/cost guidance and effort tiering (single source of truth; do not duplicate here)
- `rules/safety-irreversible.md` — safety bounds, irreversible-op confirmation, maker≠checker (the
  engineering-specific elaboration, e.g. `/autorun` gates, lives in the
  claude-engineering foundation's `loop-safety.md`, not here)
- [ADR-016](../docs/adr/016-opus-execution-guard.md) — original guard decision & implementation detail
- [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md) — guard scope extended to the thinking tier (Fable/Mythos)
- [ADR-024](../docs/adr/024-sonnet-default-main-loop.md) — default flipped to Sonnet main loop; escalation triggers
- [ADR-026](../docs/adr/026-execution-guard-role-axis.md) — guard axis changed from model to role; the model check and transcript read were removed
- `hooks/opus-execution-guard.py` — implementation
