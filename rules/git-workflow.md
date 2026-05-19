# Git Workflow

## Behavioral Rules (enforced for all agents)

These rules apply whenever any agent performs git operations — not just when `/commit`, `/create-branch`, or `/create-pr` is called explicitly.

### Commits
- **Always show the commit message to the user and get approval before committing.** Never commit silently.
- Never stage `.env`, credential files, or any file matching `*.key`, `*.pem`, `*.secret`.
- If changes span multiple unrelated purposes, split into separate commits.
- Do not push after committing — the user pushes manually.

### Branches
- **Always branch from `develop`.** Pull the latest `develop` before creating any branch.
- Never create branches from `main` or `master` unless explicitly instructed.

### Pull Requests
- **Always show the PR title and description to the user and get approval before creating.**
- Base branch is always `develop`. Never open PRs directly to `main` or `master`.
- If there are uncommitted changes, stop and guide the user to run `/commit` first.
- Do not push unless the PR flow requires it, and confirm before doing so.

---

## Commit Message Format

```
<type>: <description>

<optional body>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

Note: Attribution disabled globally via ~/.claude/settings.json.

## Pull Request Workflow

When creating PRs:
1. Analyze full commit history (not just latest commit)
2. Use `git diff [base-branch]...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan with TODOs
5. Push with `-u` flag if new branch

## Feature Implementation Workflow

1. **Plan First**
   - Use **planner** agent to create implementation plan
   - Identify dependencies and risks
   - Break down into phases

2. **TDD Approach**
   - Use **tdd-guide** agent
   - Write tests first (RED)
   - Implement to pass tests (GREEN)
   - Refactor (IMPROVE)
   - Verify 80%+ coverage

3. **Code Review**
   - Use **code-reviewer** agent immediately after writing code
   - Address CRITICAL and HIGH issues
   - Fix MEDIUM issues when possible

4. **Commit & Push**
   - Detailed commit messages
   - Follow conventional commits format
