# Migration Inventory — Asset Classification (ADR-023)

This is the auditable classification of every asset in the pre-split single
repository, bucketed into `core` / `engineering` / `work-agent` / `project-local`
/ `on-demand` / `retired`, as decided by ADR-023.

## Rules

| Asset | Bucket | Note |
|---|---|---|
| `rules/answer-only.md` | core | |
| `rules/collaboration-style.md` | core | |
| `rules/claude-efficiency.md` | core | |
| `rules/memory.md` | core | |
| `rules/role-separation.md` | core | |
| `rules/safety-irreversible.md` (new) | core | neutral safety kernel |
| `rules/secret-hygiene.md` (new) | core | neutral secret-hygiene kernel |
| `rules/coding-style.md` | engineering | |
| `rules/git-workflow.md` | engineering | |
| `rules/parallel-worktree.md` | engineering | |
| `rules/testing.md` | engineering | |
| `rules/agents.md` | engineering | |
| `rules/loop-safety.md` | engineering | domain elaboration of safety-irreversible |
| `rules/security.md` | split | secret kernel → core `secret-hygiene.md`; code-level checklist (injection/XSS/authz/rate-limit) → engineering `coding-security` |

## Commands (all 23)

| Asset | Bucket | Note |
|---|---|---|
| `commands/*.md` (analyze-task, autorun, build-fix, create-branch, create-pr, deploy, design, e2e, init-autonomous, migrate, plan, refactor-clean, requirements, respond-review, review-loop-cross-path, review-loop-cross, review-loop, rollback, tdd, test-coverage, update-codemaps, update-docs, verify-loop — 23 files) | engineering | all |

## Agents (all 18)

| Asset | Bucket | Note |
|---|---|---|
| `agents/*.md` (architect, build-error-resolver, deploy-runner, doc-updater, e2e-runner, executor, fixer, git-runner, migration-runner, planner, refactor-cleaner, requirements-analyst, review-responder, reviewer, rollback-runner, security-reviewer, task-analyst, tdd-guide — 18 files) | engineering | all |

## Skills

| Asset | Bucket | Note |
|---|---|---|
| `skills/3-line-contract/` | core | neutral task-framing |
| `skills/memory-dream/` | core | neutral KB maintenance |
| `skills/git-workflow/` | engineering | |
| `skills/loop-engineering/` (+ `reference/`) | engineering | |

## Workflows

| Asset | Bucket | Note |
|---|---|---|
| `workflows/loop-engineering-large-A.js` | engineering | |

## Templates

| Asset | Bucket | Note |
|---|---|---|
| `templates/init-autonomous/*` | engineering | |

## Hooks

| Asset | Bucket | Note |
|---|---|---|
| `hooks/secret-detection.py` | core | |
| `hooks/git-add-secret-blocker.py` | core | |
| `hooks/mass-delete-blocker.py` | core | |
| `hooks/opus-execution-guard.py` | core | |
| `hooks/doc-blocker.py` | core | |
| `hooks/test_opus_execution_guard.py` | core | |
| `hooks/protected-branch-edit-guard.py` | engineering | |
| `hooks/git-destructive-blocker.py` | engineering | |
| `hooks/pr-base-checker.py` | engineering | |
| `hooks/commit-msg-convention.py` | engineering | |
| `hooks/test_git_destructive_blocker.py` | engineering | |
| `hooks/test_pr_base_checker.py` | engineering | |
| `hooks/test_protected_branch_edit_guard.py` | engineering | |

## Docs

| Asset | Bucket | Note |
|---|---|---|
| `docs/adr/*` | core | history retained in core (repo of record) |
| `docs/autorun-flow.md` | engineering | duplicated into engineering (retired from core) |
| `docs/architecture.md` | core | scope updated to reflect the pruned core |
| `docs/requirements.md` | core | scope updated to reflect the pruned core |

## Installer / Wiring

| Asset | Bucket | Note |
|---|---|---|
| `install.py` (old) + `setup.sh` (symlink method) | retired | replaced by copy-based `installer.py` + `install.py` |
| `mcp.json` (global) | retired / project-local | no global MCP in core; MCP config moves to project-local |
| `settings.json.template` | retired | split into per-foundation `settings-fragment.json` |

## FORCE-managed settings keys

| Key | Bucket | Note |
|---|---|---|
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | core | |
| `permissions.defaultMode` | core | |
| `permissions.allow` (git / gh / claude / curl) | engineering | |
| `hooks.PreToolUse` / `hooks.PostToolUse` | split | wired per hook owner (core hooks → core fragment, engineering hooks → engineering fragment) |
| `enabledPlugins` (github, commit-commands, pr-review-toolkit, security-guidance, frontend-design) | engineering | |
| `enabledPlugins.slack` | work-agent | |
| `extraKnownMarketplaces` | pack-owned | engineering + work-agent each carry their own |
| MCP (Playwright / Figma) | project-local / on-demand | |
| MCP (Notion crien / shigetomo) + Google | work-agent | credential-less scaffold |

## Note

`work-agent` has almost no pre-existing content in the current repo — it is a new
minimal scaffold, populated only with the credential-less Notion/Google MCP
scaffolding and the `enabledPlugins.slack` flag above. Its actual business/ops
workflows are not yet defined and are out of scope for this migration.
