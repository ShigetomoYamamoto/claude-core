# Loop Safety — Autonomous Run Guardrails

Rules for running Claude in autonomous "loops" — self-paced `/loop`, `/goal`,
`ScheduleWakeup`, or `Workflow` — i.e. whenever Claude continues across turns
without a human prompt in between. A loop with no brakes is the failure mode,
not the exception.

## Preconditions (ALL required before starting a loop)

Do NOT start an autonomous loop unless every one of these holds:

1. **Clear done-condition** — completion can be stated in one sentence and is machine-verifiable.
2. **Safe workspace** — work happens on a dedicated branch or git worktree, never on `main` / `master` / `develop`.
3. **Mechanical success test** — tests / lint / type-check / a script decides success, NOT the agent's self-assessment.
4. **Hard stop** — at least one explicit limit (turns, wall-clock, or token budget) is set (see below).

If success cannot be judged mechanically (business judgment, creative direction,
"make it nice"), DO NOT loop — keep a human in the decision.

## Hard stops (CRITICAL)

Every autonomous run MUST carry at least one explicit ceiling:

- **Turn cap** — e.g. `... or stop after 20 turns`
- **Wall-clock cap** — stop after N minutes
- **Token / cost budget** — stop when the run's budget is exhausted

When the user sets no limit, default to **20 turns OR 30 minutes, whichever comes
first**, then stop and report. Never silently continue past a ceiling.

## Goal drift

- Re-state the original done-condition at the start of each iteration. If the
  current work no longer maps to it, STOP and report instead of improvising a new goal.
- The completion evaluator only sees the conversation output — make every step's
  result observable in the transcript (run the check, show the result).

## Irreversible / outward-facing actions

- Pause for explicit human confirmation before irreversible or outward-facing steps
  (`git push`, deploy, delete, sending to external services) — even mid-loop.
  Approval in one iteration does NOT carry over to the next.

## `/goal` completion-condition recipe

```
/goal <machine-checkable condition> or stop after <N> turns
```

Example: `/goal all tests in tests/auth pass and lint is clean, or stop after 15 turns`

- The condition must be provable from Claude's own output (run the test, show the
  result) — not "looks done".
- A fast model re-checks the condition after every turn and auto-clears the goal
  when it holds.

## Cost awareness

- Multi-agent fan-out can cost ~15x a single chat. Prefer the smallest fleet that
  covers the work, and report what was intentionally skipped — silent truncation
  reads as "covered everything" when it wasn't.
