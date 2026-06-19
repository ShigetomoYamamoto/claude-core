# Autorun Flow — Declarative Flow Definition (the autonomous transition table)

The single source of truth for the *shape* of the full pipeline, read by the
`/autorun` interpreter. It holds no execution logic — only **which phases run, in
what order, and where to stop**. Each phase's body is handled by existing commands /
agents / skills (parts are reused). The safety norm of record is `rules/loop-safety.md`.

## Modes (two modes = a difference of start/goal parameters)

| Mode | start | first phase | goal |
|------|-------|-------------|------|
| full-auto | a free-form objective | requirements | deploy |
| support | a concrete task / Issue | analyze-task | pr |

The two modes are not separate engines — the same transition table is given
different start/goal parameters.

## Phase transition table

| phase_id | execution part | kind | success_test (decided mechanically) | full-auto next | support next |
|----------|----------------|------|-------------------------------------|----------------|-------------|
| requirements | requirements-analyst | **gate** | human approves the requirements | design | — |
| analyze-task | task-analyst | auto | breakdown + acceptance criteria produced | plan | plan |
| design | architect | **gate** (skippable) | human approves the design | plan | plan |
| plan | planner | auto | the plan has file paths and ordered steps | tdd | tdd |
| tdd | `skills/loop-engineering/` (delegated to the micro layer) | auto | tests/lint/typecheck pass and coverage 80%+ (measured via Bash) | verify | verify |
| verify | `/review-loop` (delegated) | auto | reviewer returns NO_ISSUES and mechanical checks pass | commit | commit |
| commit | `/commit-commands:commit` | auto (※) | code-reviewer CRITICAL/HIGH=0 and secret-detection passes | pr | pr |
| pr | `/create-pr` | **gate** | human approves the PR (push/PR via gh) | migrate | (goal) |
| migrate | `/migrate` | auto (destructive changes confirmed) | migration succeeds | deploy | — |
| deploy | `/deploy` | **gate** | human approves the deploy | (goal) | — |

※ commit is kind=auto only because `/autorun` obtained a one-time blanket approval
for auto-commits at startup (`rules/git-workflow.md` autonomous-run exception). The
message is shown in the transcript every time. Without that approval, treat commit as a gate.

## Gates (kind=gate, the human always confirms)

- **requirements** — direction that cannot be judged mechanically (are the requirements right?). Largest rework cost.
- **design** — same (architecture decisions). May be skipped if the skip condition below holds.
- **pr** — outward-facing, irreversible (`git push`).
- **deploy** — irreversible production change.

The norm for irreversible stop points (pr / deploy / migrate destructive changes) is `rules/loop-safety.md`.

## design skip decision (input = the requirements phase output)

When design is reached, plan has not run yet, so judge from the **requirements
output**. Have requirements-analyst emit a "needs new DB schema / new API / tech
selection / system-boundary change?" flag; if all are unnecessary, skip the design
gate and auto-advance to plan (don't stop or skip by mistake).

## Mechanical verifiability check (at startup)

At `/autorun` startup, detect via Bash whether every auto phase's success_test is
mechanically verifiable in this project (existence of test / lint / typecheck
commands). If any is undetectable, stop early with "cannot self-run — reporting
what's missing" (avoid stalling mid-run).

## Whitelist of places it may stop

An autonomous run may stop ONLY at:

1. The four gates (requirements / design / pr / deploy)
2. A hard stop (below, two-layer)
3. A per-phase retry cap
4. Goal reached (full-auto=deploy / support=pr)
5. Startup precondition / verifiability failure (early stop)
6. Irreversible-op confirmation (migrate DROP/RENAME etc., all irreversible ops defined in `rules/loop-safety.md`)
7. Unrecoverable error (e.g. build-error-resolver hitting its cap)

Stopping anywhere else is a definition violation — detect and report it.

## Hard stop (two-layer)

- **Per-phase budget**: verify=5 rounds, tdd=the micro layer (loop-engineering) internal cap. Per-phase default.
- **Whole-run budget**: a total transition-count cap + the session ceiling in `rules/loop-safety.md` (default 20 turns / 30 min). The per-phase and whole-run budgets are independent; whichever is hit first stops the run.

## Single-command use (RUN_STATE not declared)

When a command is invoked directly (`/requirements` etc.), this flow definition does
not apply and each command falls back to its **conventional guided stop**. The kind
values here take effect only in an autonomous run (where RUN_STATE is declared).

## Related

- `commands/autorun.md` — the interpreter that reads this definition
- `rules/loop-safety.md` — the safety norm of record (hard stop / goal drift / irreversible ops)
- `docs/adr/007-autonomous-loop-execution.md` — the four-gate decision
- `docs/adr/008-orchestration-declarative-flow.md` — the declarative-flow decision and commit blanket approval
- `skills/loop-engineering/SKILL.md` — the tdd phase's execution part (micro layer)
