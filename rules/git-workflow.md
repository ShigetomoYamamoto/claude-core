# Git Workflow

## Behavioral Rules (enforced for all agents)

These rules apply whenever any agent performs git operations — not just when `/commit`, `/create-branch`, or `/create-pr` is called explicitly.

### Commits
- **Always show the commit message to the user and get approval before committing.** Never commit silently.
- Never stage `.env`, credential files, or any file matching `*.key`, `*.pem`, `*.secret`.
- If changes span multiple unrelated purposes, split into separate commits.
- Do not push after committing — the user pushes manually.
- **Autonomous-run exception:** during `/autorun`, the user grants a one-time blanket approval for auto-commits at startup; per-commit approval is then waived (the message is still shown in the transcript each time). Without that approval, commit becomes a gate. See `docs/adr/008-orchestration-declarative-flow.md`.

### Branches
- **Always branch from `develop`.** Pull the latest `develop` before creating any branch.
- Never create branches from `main` or `master` unless explicitly instructed.

### Pull Requests
- **Always show the PR title and description to the user and get approval before creating.**
- Base branch is always `develop`. Never open PRs directly to `main` or `master`.
- If there are uncommitted changes, stop and guide the user to run `/commit` first.
- Do not push unless the PR flow requires it, and confirm before doing so.

---

## Reference

Format details (Conventional Commits type table / branch naming conventions / PR description template) are documented in `~/.claude/skills/git-workflow/SKILL.md`. Refer to it when generating commit messages, branch names, or PR descriptions.
