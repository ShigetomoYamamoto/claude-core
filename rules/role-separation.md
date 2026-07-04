# Role Separation — Thinking Tier (Fable/Opus) vs Execution (Sonnet/Haiku)

## The principle

Split work across models by role: **the thinking tier (Fable 5 / Opus) thinks, Sonnet/Haiku execute.**

| | Thinking tier (Fable 5 / Opus 4.8) | Sonnet (5 / 4.6) | Haiku 4.5 |
|---|---|---|---|
| **Best for** | thinking, consultation, research, planning, delegation decisions | editing, deletion, state-changing Bash, repetitive work, tool operations | lightweight agents, worker tasks, frequent calls |

The point: hand work that does NOT need deep thinking (obvious execution, mechanical repetition, tool operations) to Sonnet/Haiku, and keep the thinking tier on the decisions that actually need judgment. Model performance/cost detail lives in `rules/claude-efficiency.md` (single source of truth — this file defines only the role split).

## Enforcement: the opus-execution-guard hook

`hooks/opus-execution-guard.py` ([ADR-016](../docs/adr/016-opus-execution-guard.md), scope extended by [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md)) blocks the **main-loop thinking-tier model** from executing state-changing operations:

- **Edit tools**: `Edit` / `Write` / `MultiEdit` / `NotebookEdit`
- **State-changing Bash** (denylist): `rm` / `mv` / `cp` / `tee` / `mkdir` / `sed -i` / `git add|commit|push|reset|clean` / `npm|pip install` / redirection `>` `>>`, etc.

It reads the active model from the transcript's latest assistant `message.model`; if it is a thinking-tier model (`claude-opus-*` / `claude-fable-*` / `claude-mythos-*`), the operation is blocked with `exit 2`. **Allowed even on the thinking tier**: read-only Bash (`ls`, `cat`, `git status|diff|log`), test/lint/typecheck runs, and `Task` delegation.

**Always allowed (pass with exit 0):** subagents (stdin carries `agent_id` → treated as the delegated execution layer), Sonnet/Haiku, and any case where the model cannot be determined (fail-open, per [ADR-006](../docs/adr/006-hook-error-policy.md)).

## Physical-layer scope (do not overstate — aligned with [ADR-014](../docs/adr/014-loop-engineering-as-discipline.md))

The hook fires **only** on Bash and `Edit|Write|MultiEdit|NotebookEdit`. It does **NOT** fire on MCP-routed tool calls (Playwright, repeated MCP ops) or on deploy/migrate/rollback commands. Those are covered by this norm plus the executing agents' `model: sonnet` declaration — never claim the hook guards them.

## Two ways to switch to execution

1. **Manual** — run `/model sonnet` in the main conversation; switch back with `/model fable` (or `/model opus`).
2. **Delegation** — hand the edit/change to an execution agent via `Task`:
   - `git-runner` — VCS / release execution (stage / commit / push / PR / branch / merge)
   - `executor` — general edits / Bash outside any specialist's charter
   - `fixer` — code fixes / error handling
   - `tdd-guide` — test-driven development (tests + implementation)
   - `build-error-resolver` — build / type-error fixes
   - `e2e-runner` — Playwright E2E

   These agents declare `model: sonnet` (already 100% in place), so a delegated edit passes the guard's `agent_id` gate.

   Do NOT delegate execution to the built-in `general-purpose` / `claude` agent: it inherits the parent (Opus) model, so it runs expensive and off-role (even though the `agent_id` gate would let it through). Use the dedicated `model: sonnet` runners above, or pass `model: sonnet` explicitly in the `Task` call.

## Tool operations

Browser automation and repeated MCP execution belong to Sonnet:
- **Design** (how to drive it): Opus's judgment.
- **Execution** (running the steps): delegate to Sonnet, or `/model sonnet`.

Example: design a complex Playwright scenario on Opus; run it and reproduce bugs on Sonnet.

## loop-engineering note

`skills/loop-engineering/SKILL.md` STEP 4 onward (implementation = edits + state-changing Bash) is "execution." On a thinking-tier model it is blocked by the guard; switch to Sonnet or delegate to `fixer` / `tdd-guide`. Under `/autorun`, the tdd phase delegates implementation to a Sonnet agent when the main model is in the thinking tier.

## Related

- `rules/claude-efficiency.md` — model performance/cost guidance (single source of truth; do not duplicate here)
- `rules/loop-safety.md` — safety bounds & irreversible-op confirmation
- [ADR-016](../docs/adr/016-opus-execution-guard.md) — decision & implementation detail
- [ADR-020](../docs/adr/020-thinking-tier-execution-guard.md) — guard scope extended to the thinking tier (Fable/Mythos)
- `hooks/opus-execution-guard.py` — implementation
