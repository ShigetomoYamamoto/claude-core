# Security Guidelines

## Mandatory Security Checks

Before ANY commit:
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized HTML)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on all endpoints
- [ ] Error messages don't leak sensitive data

## Secret Management

- NEVER hardcode secrets (API keys, passwords, tokens) in source files
- ALWAYS load secrets from environment variables
- Validate required env vars at startup and fail fast with a clear error if missing
- Add `.env` and credential files to `.gitignore`

## Secret guard layers (defense in depth)

「秘密を守る」責務は3層に分かれる。どれが**決定的(止める)**でどれが**検出(警告のみ)**かを混同しないこと:

| 層 | 実体 | 動作 | 限界 |
|---|---|---|---|
| 規範(ソフト) | この `security.md`・`rules/git-workflow.md` | 「ハードコード禁止」等の規律 | LLM の遵守に依存 |
| ステージ時ハードブロック | `hooks/git-add-secret-blocker.py` | `git add` で秘匿ファイルを exit 2 で阻止 | `commit -a` / stash / 動的ファイル名は捕捉できない |
| 書込後の検出(警告) | `hooks/secret-detection.py` | Edit/Write 後にパターン検査し警告(exit 2 なし) | 止めない。人間/後続が拾う前提 |

不可逆(漏洩)を**決定的に止める**のは add 時のみ。それ以外は検出に留まる、と理解すること(ADR-014 / `rules/loop-safety.md` の物理層)。

## Security Response Protocol

If security issue found:
1. STOP immediately
2. Use **security-reviewer** agent
3. Fix CRITICAL issues before continuing
4. Rotate any exposed secrets
5. Review entire codebase for similar issues
