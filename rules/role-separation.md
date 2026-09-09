# Role Separation — Opus Default Main Loop, Sonnet Execution Layer, Fable for Escalation

## The principle

**Default: Opus 5 runs the main loop.** The main loop cannot execute at all (see the guard
below): its job is to read, judge, decompose, delegate, and verify. That non-executing
orchestrator seat gets the frontier-grade judgment — putting the cheapest model there was
ADR-024's mismatch, reversed by
[ADR-029](../docs/adr/029-opus-default-main-loop.md).

**Sonnet (5 / 4.6) is the default execution layer**, Haiku 4.5 for lightweight/high-frequency
workers. This is unchanged by the flip — the concrete execution agents already pin
`model: sonnet`.

**Fable 5 is a further escalation, reached from Opus — not a default alternative to it.**
Two conditions must BOTH hold:

1. the case hits one of these five (the primary screen):
   - Resolving ambiguous requirements
   - Architecture / foundational decisions
   - Non-obvious or platform-dependent risk
   - Confirming constraints before a destructive/irreversible operation
   - Final approval of a significant change
2. **and** the problem clears the Fable bar: indivisible, must be reviewed as a whole in one
   context, needs maximum reasoning depth (e.g. knowledge-base consolidation, system-wide
   design review).

Hitting the five alone is no longer a reason to escalate — under an Opus main loop those are
its ordinary work (ADR-029; they were written when the main loop was the cheap model).

| | Opus 5 — default main loop | Sonnet (5 / 4.6) — default execution layer | Fable 5 — escalation only | Haiku 4.5 |
|---|---|---|---|---|
| **Best for** | judging, decomposing, delegating, verifying; the five above | implementation, edits, git, tests, tool-driving — all actual execution | indivisible whole-context problems at maximum depth | lightweight agents, worker tasks, frequent calls |

Execution is **delegated to Sonnet, never run by the main loop** — that is a delegation, not a
model switch. **Maker ≠ checker** for significant changes: get independent review (a separate
Sonnet session, or a second Opus pass) rather than self-certifying — see
`rules/safety-irreversible.md`. Model cost/perf detail and effort tiering live in
`rules/claude-efficiency.md` (single source of truth — this file defines only the role split).

## Enforcement: the main-loop-execution-guard hook

`hooks/main-loop-execution-guard.py` ([ADR-016](../docs/adr/016-opus-execution-guard.md),
extended by [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md), reframed by
[ADR-024](../docs/adr/024-sonnet-default-main-loop.md), **axis replaced by
[ADR-026](../docs/adr/026-execution-guard-role-axis.md)**) enforces the split
mechanically. It keys on **role, not model**: the only thing it reads from stdin is
whether `agent_id` is present. ADR-029's flip of the default therefore needs **no hook change**.

- **Main loop** (no `agent_id`) — cannot run `Edit` / `Write` / `MultiEdit` /
  `NotebookEdit`, nor state-changing Bash (`rm` / `mv` / `cp` / `tee` / `mkdir` /
  `sed -i` / `git add|commit|push|reset|clean` / `npm|pip install` / redirection).
  **This holds on every model, whatever the main loop is running** — that is the point of
  ADR-026.
- **Execution layer** (stdin carries `agent_id`) — unrestricted. This is where the
  work happens.
- **Two path exceptions for the main loop**: auto-memory
  (`~/.claude/projects/*/memory/`) and the session scratchpad. Nothing else. The
  boundary is fixed absolute paths, never a judgment about whether a file is
  "config" or "product code" — in a config repo like claude-core those are the same
  files (ADR-026). For Bash these two paths are honored only when redirection is the
  *sole* mutating element and the target is an absolute path under them — `rm` / `cp`
  / `git add` stay blocked even inside those paths (ADR-028).
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

The hook fires **only** on Bash and `Edit|Write|MultiEdit|NotebookEdit`. It does **NOT** fire on MCP-routed tool calls (Playwright, repeated MCP ops) or on deploy/migrate/rollback commands. Those are covered by this norm plus the executing agents' `model: sonnet` declaration — never claim the hook guards them. With an Opus main loop this gap costs money as well as discipline (see "Tool operations").

## Delegating and escalating

1. **Delegate first** — execution work goes to a Sonnet subagent via the `Agent` tool
   (`model: sonnet`). A subagent declaring `model: sonnet` passes the guard's `agent_id`
   gate regardless of what the main loop is running.
   - **Pass `run_in_background: false`** where the harness supports it. Subagents run in the
     background by default (Claude Code 2.1.198+), so a fire-and-forget delegation ends the
     turn and the loop stalls even after the subagent finishes. Wait for the report, then
     continue.
   - **Never ask the user to switch models.** Delegation is something you can do
     yourself, right now; `/model sonnet` is a user action and is not a substitute
     for delegating.
   - **Always pass `model: sonnet` explicitly.** The built-in `general-purpose` / `claude`
     agents inherit the parent model, which is now Opus by default — so an unpinned
     delegation runs expensive and off-role (even though the `agent_id` gate lets it
     through).
   - The concrete engineering execution agents (`git-runner`, `executor`, `fixer`,
     `tdd-guide`, `build-error-resolver`, `e2e-runner`) live in the
     claude-engineering foundation, not here.
2. **Escalate** — Opus → Fable only, and only when both conditions above hold:
   `/model fable`.
3. **Return** — once the Fable-level judgment call is made, resume on Opus
   (`/model opus`); Opus is the default, so this is usually just continuing the main
   conversation.

## Tool operations

**Execution stays pinned to Sonnet even under an Opus main loop** ([ADR-029](../docs/adr/029-opus-default-main-loop.md) decided this explicitly, rather than moving it with the default):

- **Design** (how to drive it — the scenario, the step order): the main loop's job, so Opus by default.
- **Execution** (running the steps — browser automation, repeated MCP ops): **delegate to Sonnet.** Mechanical driving does not need the smarter model.

This one matters more than it used to: the guard does **not** fire on MCP-routed calls, so an
Opus main loop that drives MCP tools directly burns frontier tokens on mechanical work with
**no mechanical stop**. This pin is norm-only — nothing enforces it.

Example: designing a Playwright scenario stays in the main loop (Opus); running it goes to a
`model: sonnet` subagent.

## Related

- `rules/claude-efficiency.md` — model performance/cost guidance and effort tiering (single source of truth; do not duplicate here)
- `rules/safety-irreversible.md` — safety bounds, irreversible-op confirmation, maker≠checker (the
  engineering-specific elaboration, e.g. `/autorun` gates, lives in the
  claude-engineering foundation's `loop-safety.md`, not here)
- [ADR-016](../docs/adr/016-opus-execution-guard.md) — original guard decision & implementation detail
- [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md) — guard scope extended to the thinking tier (Fable/Mythos)
- [ADR-024](../docs/adr/024-sonnet-default-main-loop.md) — default flipped to Sonnet main loop (superseded on the default by ADR-029; its escalation concept survives)
- [ADR-026](../docs/adr/026-execution-guard-role-axis.md) — guard axis changed from model to role; the model check and transcript read were removed
- [ADR-028](../docs/adr/028-command-string-guard-limits.md) — the guard judges command strings, not effects; the norm is the primary defense and the pattern layer is knowingly incomplete
- [ADR-029](../docs/adr/029-opus-default-main-loop.md) — default flipped back to Opus main loop; five conditions rescoped to the Opus→Fable screen; Tool-operations execution stays Sonnet-pinned
- `hooks/main-loop-execution-guard.py` — implementation
