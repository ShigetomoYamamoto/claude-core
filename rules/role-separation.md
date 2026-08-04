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
scope extended by [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md), framing
updated by [ADR-024](../docs/adr/024-sonnet-default-main-loop.md)) enforces the
hand-back above: it blocks the **active thinking-tier model** from executing
state-changing operations, whenever it is active — mid-escalation or otherwise:

- **Edit tools**: `Edit` / `Write` / `MultiEdit` / `NotebookEdit`
- **State-changing Bash** (denylist): `rm` / `mv` / `cp` / `tee` / `mkdir` / `sed -i` / `git add|commit|push|reset|clean` / `npm|pip install` / redirection `>` `>>`, etc.

It reads the active model from the transcript's latest assistant `message.model`; if
it is a thinking-tier model (`claude-opus-*` / `claude-fable-*` / `claude-mythos-*`),
the operation is blocked with `exit 2`. **Allowed even on the thinking tier**:
read-only Bash (`ls`, `cat`, `git status|diff|log`), test/lint/typecheck runs, and
`Task` delegation.

**Always allowed (pass with exit 0):** subagents (stdin carries `agent_id` → treated
as the delegated execution layer), Sonnet/Haiku, and any case where the model cannot
be determined (fail-open, per [ADR-006](../docs/adr/006-hook-error-policy.md)).

The guard's mechanism did not change when the default flipped to Sonnet — only which
model is normally active did. It still exists to catch the same mistake: a
thinking-tier session editing directly instead of handing back to Sonnet.

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

## loop-engineering note (engineering foundation only)

The TDD/implementation loop mechanics that apply this principle (e.g. the
implementation phase of a test-driven loop being blocked on a thinking-tier
model) live in `skills/loop-engineering/` in the claude-engineering foundation,
not here — this file states only the underlying model-role principle it depends on.

## Related

- `rules/claude-efficiency.md` — model performance/cost guidance and effort tiering (single source of truth; do not duplicate here)
- `rules/safety-irreversible.md` — safety bounds, irreversible-op confirmation, maker≠checker (the
  engineering-specific elaboration, e.g. `/autorun` gates, lives in the
  claude-engineering foundation's `loop-safety.md`, not here)
- [ADR-016](../docs/adr/016-opus-execution-guard.md) — original guard decision & implementation detail
- [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md) — guard scope extended to the thinking tier (Fable/Mythos)
- [ADR-024](../docs/adr/024-sonnet-default-main-loop.md) — default flipped to Sonnet main loop; escalation triggers; guard mechanism unchanged
- `hooks/opus-execution-guard.py` — implementation
