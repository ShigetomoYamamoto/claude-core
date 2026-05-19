# Hooks System

  ## Hook Types

  - **PreToolUse**: Before tool execution (validation, parameter modification)
  - **PostToolUse**: After tool execution (auto-format, checks)
  - **Stop**: When session ends (final verification)

  ## Current Hooks (in ~/.claude/settings.json)

  ### PreToolUse
  - **doc blocker** (`Write`): Blocks creation of new `.md` / `.txt` files. Allows
  `CLAUDE.md`, `docs/`, `.claude/` paths. Script: `~/.claude/hooks/doc-blocker.py`

  ### PostToolUse
  - **console.log warning** (`Edit|Write|MultiEdit`): Warns when `console.log` is detected
  after editing JS/TS files. Script: `~/.claude/hooks/console-log-warning.py`
  - **secret detection** (`Edit|Write|MultiEdit`): Warns when hardcoded API keys, JWTs, or
  passwords are detected. Script: `~/.claude/hooks/secret-detection.py`

  ### Stop
  - **Audio notification**: Plays Glass.aiff on macOS (`afplay`), falls back to terminal bell (`printf '\a'`) on Linux
  - **console.log audit**: Scans all modified files for `console.log` before session ends.
  Script: `~/.claude/hooks/console-log-audit.py`

  ### PermissionRequest
  - **Audio notification**: Plays Ping.aiff on macOS (`afplay`), falls back to terminal bell (`printf '\a'`) on Linux

  ## Hook Scripts

  All scripts live in `~/.claude/hooks/`:

  | File | Trigger | Action |
  |---|---|---|
  | `doc-blocker.py` | PreToolUse(Write) | Block unnecessary .md/.txt creation |
  | `console-log-warning.py` | PostToolUse(Edit/Write/MultiEdit) | Immediate console.log
  warning |
  | `secret-detection.py` | PostToolUse(Edit/Write/MultiEdit) | Detect hardcoded secrets |
  | `console-log-audit.py` | Stop | Final console.log audit at session end |

  ## Auto-Accept Permissions

  Use with caution:
  - Enable for trusted, well-defined plans
  - Disable for exploratory work
  - Never use dangerously-skip-permissions flag
  - Configure `allowedTools` in `~/.claude/settings.json` instead