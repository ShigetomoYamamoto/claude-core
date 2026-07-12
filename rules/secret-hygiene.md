# Secret Hygiene (domain-neutral)

- NEVER hardcode secrets (API keys, passwords, tokens) in any file.
- Load secrets from environment variables or an OS keychain; validate required
  vars at startup and fail fast with a clear error if one is missing.
- Add `.env` and credential files to `.gitignore`. Never stage `.env`, `*.key`,
  `*.pem`, `*.secret`.
- Never write a secret into memory, notes, logs, or documents.

## Defense-in-depth layers (know which one actually stops a leak)

| Layer | Mechanism | Behavior |
|---|---|---|
| Norm (soft) | this rule | discipline; relies on the agent obeying |
| Stage-time hard block | `git-add-secret-blocker.py` hook | exit 2 on `git add` of a secret file |
| Post-write detection | `secret-detection.py` hook | warns after Edit/Write (does NOT stop) |

Only the stage-time block is decisive; the rest are detection. If a secret is
exposed: STOP, rotate it, and scrub it from history. Code-level security review
(injection, XSS, authz, rate limiting) is the engineering foundation's concern.
