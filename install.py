#!/usr/bin/env python3
"""Install Claude Code global config from this repo into ~/.claude.

Design (why this is not a plain copy):
  ~/.claude mixes two kinds of content with opposite needs.

  1. Static, repo-owned dirs (agents/commands/rules/skills/hooks/workflows/docs).
     Never written by Claude at runtime -> linked as SYMLINKS to this repo, so a
     repo edit goes live immediately and `git pull` updates every machine. No
     `rm -rf` of real content, no copy drift.

  2. settings.json. Written by Claude AT RUNTIME (/effort, /model, plugin toggles,
     "always allow" permissions). A blind overwrite destroys that state -- this is
     what wiped the notification settings before. So it is MERGED, never replaced,
     using just two rules:
       FORCE   (repo wins, so wiring propagates): hooks.PreToolUse / PostToolUse,
               permissions.allow (union), env (per key), enabledPlugins,
               extraKnownMarketplaces. The live value takes the template's; to
               remove forced wiring, set it empty in the template (its absence
               leaves live untouched rather than deleting it).
       DEFAULT (fill only when the key is absent in live; a present live value
               always wins -- this is how notifications survive): everything else,
               e.g. hooks.Stop / PermissionRequest / Notification, model, effortLevel.
     A live key is never deleted, and the file is backed up before writing.

  3. mcp.json -> additive merge into ~/.claude.json (only adds missing servers).

Usage:
  python3 install.py            apply
  python3 install.py --dry-run  show what would change, write nothing
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"

STATIC_DIRS = ["agents", "commands", "rules", "skills", "hooks", "workflows", "templates", "docs"]

# settings.json merge policy (see module docstring)
FORCE_HOOK_EVENTS = ["PreToolUse", "PostToolUse"]
FORCE_DICT_KEYS = ["env", "enabledPlugins", "extraKnownMarketplaces"]


# ─────────────────────────────────────────────────────────────
# output helpers
# ─────────────────────────────────────────────────────────────
def ok(msg):
    print(f"  ✓ {msg}")


def warn(msg):
    print(f"  ⚠ {msg}")


def info(msg):
    print(f"    {msg}")


def step(msg):
    print(f"\n{msg}")


def fail(msg):
    print(f"  ✗ {msg}", file=sys.stderr)
    sys.exit(1)


def fmt_names(names, limit=6):
    """Join names for display, truncating long lists."""
    names = [str(n) for n in names]
    if len(names) <= limit:
        return ", ".join(names)
    return ", ".join(names[:limit]) + f" 他{len(names) - limit}件"


# ─────────────────────────────────────────────────────────────
# backup (created lazily, only when something is actually backed up)
# ─────────────────────────────────────────────────────────────
class Backup:
    """Timestamped backup dir under ~/.claude/.backup, created on first use."""

    def __init__(self, dry_run, stamp):
        self.dry_run = dry_run
        self.root = CLAUDE_DIR / ".backup" / stamp
        self.used = False

    def save(self, path):
        """Copy a file or directory into the backup, mirroring its path under ~/.claude."""
        if not path.exists() and not path.is_symlink():
            return
        try:
            rel = path.relative_to(CLAUDE_DIR)
        except ValueError:
            rel = Path(path.name)
        dest = self.root / rel
        if self.dry_run:
            info(f"バックアップ予定: {path} → {dest}")
            self.used = True
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir() and not path.is_symlink():
            shutil.copytree(path, dest, symlinks=True)
        else:
            shutil.copy2(path, dest)
        self.used = True


# ─────────────────────────────────────────────────────────────
# Step 1: preflight
# ─────────────────────────────────────────────────────────────
def preflight():
    step("[1/4] 事前チェック")

    if sys.version_info < (3, 8):
        fail(f"python {sys.version_info.major}.{sys.version_info.minor} は古すぎます（3.8 以上が必要）")
    ok(f"python {sys.version_info.major}.{sys.version_info.minor}")

    if shutil.which("git"):
        ok("git: 検出")
    else:
        fail("git が見つかりません（2.0 以上が必要）")


# ─────────────────────────────────────────────────────────────
# Step 2: symlink static dirs
# ─────────────────────────────────────────────────────────────
def dir_content_diff(live_dir, repo_dir):
    """Compare a live real dir against the repo dir it will link to.

    Returns (added, removed, modified) as lists of relative paths:
      added    = files the repo has that live lacks -> appear after linking
      removed  = files live has that the repo lacks -> disappear after linking
      modified = files in both whose contents differ -> updated to the repo version
    """
    def files(root):
        return {p.relative_to(root): p for p in root.rglob("*") if p.is_file()}

    def differ(a, b):
        try:
            return a.read_bytes() != b.read_bytes()
        except OSError:
            return True  # unreadable -> treat as modified (never hide a real change)

    live, repo = files(live_dir), files(repo_dir)
    live_set, repo_set = set(live), set(repo)
    added = sorted(repo_set - live_set)
    removed = sorted(live_set - repo_set)
    modified = sorted(p for p in (live_set & repo_set) if differ(live[p], repo[p]))
    return added, removed, modified


def _report_dir_diff(name, live_dir, repo_dir):
    """Print what switching this dir from a real copy to a symlink will change."""
    added, removed, modified = dir_content_diff(live_dir, repo_dir)
    if not (added or removed or modified):
        info(f"{name}/ コピー実体 → symlink（中身は repo と同一・実質変化なし）")
        return
    info(f"{name}/ コピー実体 → symlink（中身が更新されます）")
    if modified:
        info(f"  変更 {len(modified)}: {fmt_names(modified)}")
    if added:
        info(f"  追加 {len(added)}: {fmt_names(added)}")
    if removed:
        info(f"  消失 {len(removed)}: {fmt_names(removed)}")


def link_dirs(dry_run, backup):
    step("[2/4] 設定ディレクトリのリンク作成")

    for name in STATIC_DIRS:
        src = REPO / name
        if not src.is_dir():
            continue
        dst = CLAUDE_DIR / name

        if dst.is_symlink() and dst.exists() and dst.resolve() == src.resolve():
            ok(f"{name}/ （リンク済み・変化なし）")
            continue

        # Replace whatever is there, backing up real dirs first.
        if dst.is_symlink():
            if not dry_run:
                dst.unlink()
            info(f"{name}/ （古いリンクを repo への symlink に置換）")
        elif dst.is_dir():
            _report_dir_diff(name, dst, src)
            backup.save(dst)
            if not dry_run:
                shutil.rmtree(dst)
        elif dst.exists():
            backup.save(dst)
            if not dry_run:
                dst.unlink()

        if dry_run:
            ok(f"{name}/ → {src} にリンク予定")
        else:
            CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=True)
            ok(f"{name}/ → {src}")


# ─────────────────────────────────────────────────────────────
# Step 3: merge settings.json
# ─────────────────────────────────────────────────────────────
def _union(a, b):
    """Order-preserving union of two lists."""
    return list(dict.fromkeys(list(a) + list(b)))


def merge_settings_data(template, live):
    """Pure merge per the policy in the module docstring. Never deletes a live key."""
    result = dict(live)  # start from live so every live key survives

    # FORCE per-key dicts: template wins on its own keys, live extras kept
    for key in FORCE_DICT_KEYS:
        if key in template or key in live:
            result[key] = {**live.get(key, {}), **template.get(key, {})}

    # permissions: template defaults < live, but allow lists are unioned
    if "permissions" in template or "permissions" in live:
        perms = {**template.get("permissions", {}), **live.get("permissions", {})}
        t_allow = template.get("permissions", {}).get("allow", [])
        l_allow = live.get("permissions", {}).get("allow", [])
        if t_allow or l_allow:
            perms["allow"] = _union(t_allow, l_allow)
        result["permissions"] = perms

    # hooks: FORCE the blocker events from template, PRESERVE the rest of live,
    # DEFAULT-fill any template-only events.
    t_hooks = template.get("hooks", {})
    l_hooks = live.get("hooks", {})
    if t_hooks or l_hooks:
        hooks = dict(l_hooks)
        for event in FORCE_HOOK_EVENTS:
            if event in t_hooks:
                hooks[event] = t_hooks[event]  # template authoritative; [] clears it
            # template silent on this event -> leave live untouched (never delete)
        for event, value in t_hooks.items():
            if event not in FORCE_HOOK_EVENTS and event not in hooks:
                hooks[event] = value
        result["hooks"] = hooks

    # DEFAULT: any remaining template top-level key fills only when absent in live
    for key, value in template.items():
        if key not in result:
            result[key] = value

    return result


def load_template():
    raw = (REPO / "settings.json.template").read_text()
    raw = raw.replace("__HOME__", str(Path.home()))
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"settings.json.template が不正な JSON です: {exc}")


def _hook_cmds(hooks):
    """Flatten a hooks dict into a set of (event, short-command) pairs.

    Tolerant of malformed live settings (hand-edited / old schema): any value
    that isn't the expected shape is skipped rather than crashing.
    """
    pairs = set()
    if not isinstance(hooks, dict):
        return pairs
    for event, blocks in hooks.items():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            for h in block.get("hooks", []):
                if not isinstance(h, dict):
                    continue
                cmd = h.get("command", "")
                pairs.add((event, cmd.split("/")[-1] if "/" in cmd else cmd))
    return pairs


def report_settings_change(live, merged):
    """Print exactly which keys are added / changed / unchanged."""
    added = [k for k in merged if k not in live]
    changed = [k for k in merged if k in live and merged[k] != live[k]]
    removed = [k for k in live if k not in merged]  # invariant: should stay empty
    unchanged = [k for k in merged if k in live and merged[k] == live[k]]

    info(f"追加キー: {', '.join(added) if added else '（なし）'}")
    info(f"変更キー: {', '.join(changed) if changed else '（なし）'}")
    if "hooks" in changed:
        before, after = _hook_cmds(live.get("hooks", {})), _hook_cmds(merged.get("hooks", {}))
        for event, cmd in sorted(after - before):
            info(f"  + {event}: {cmd}")
        for event, cmd in sorted(before - after):
            info(f"  - {event}: {cmd}")
    if "permissions" in changed:
        before = live.get("permissions", {}).get("allow", [])
        for x in merged.get("permissions", {}).get("allow", []):
            if x not in before:
                info(f"  + permissions.allow: {x}")
    if removed:
        info(f"⚠ 削除キー（想定外）: {', '.join(removed)}")
    info(f"変更なし: {', '.join(unchanged) if unchanged else '（なし）'}")


def merge_settings(dry_run, backup):
    step("[3/4] settings.json をマージ")

    tmpl_path = REPO / "settings.json.template"
    if not tmpl_path.exists():
        fail("settings.json.template が見つかりません")

    template = load_template()
    settings_path = CLAUDE_DIR / "settings.json"
    live = {}
    if settings_path.exists():
        try:
            live = json.loads(settings_path.read_text())
        except json.JSONDecodeError as exc:
            fail(f"既存の settings.json が不正な JSON です: {exc}")

    merged = merge_settings_data(template, live)

    if merged == live:
        ok("settings.json （最新のため変更なし）")
        return

    if dry_run:
        ok("settings.json （マージ予定。既存キーは保持）")
        report_settings_change(live, merged)
        backup.save(settings_path)
        return

    backup.save(settings_path)
    text = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"
    settings_path.write_text(text)
    ok("settings.json （マージ完了）")
    report_settings_change(live, merged)


# ─────────────────────────────────────────────────────────────
# Step 4: merge mcp.json into ~/.claude.json (additive)
# ─────────────────────────────────────────────────────────────
def merge_mcp(dry_run):
    step("[4/4] mcpServers を ~/.claude.json にマージ")

    mcp_path = REPO / "mcp.json"
    if not mcp_path.exists():
        warn("mcp.json が見つからないためスキップ")
        return

    try:
        mcp = json.loads(mcp_path.read_text())
    except json.JSONDecodeError as exc:
        fail(f"mcp.json が不正な JSON です: {exc}")

    claude_path = Path.home() / ".claude.json"
    claude = {}
    if claude_path.exists():
        try:
            claude = json.loads(claude_path.read_text())
        except json.JSONDecodeError as exc:
            fail(f"既存の ~/.claude.json が不正な JSON です: {exc}")

    existing = claude.get("mcpServers", {})
    added = [k for k in mcp.get("mcpServers", {}) if k not in existing]

    if not added:
        ok("最新のため変更なし")
        return

    if dry_run:
        ok(f"追加予定: {', '.join(added)}")
        return

    for key in added:
        existing[key] = mcp["mcpServers"][key]
    claude["mcpServers"] = existing
    claude_path.write_text(json.dumps(claude, indent=2) + "\n")
    ok(f"追加: {', '.join(added)}")


# ─────────────────────────────────────────────────────────────
def main():
    dry_run = "--dry-run" in sys.argv[1:]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = Backup(dry_run, stamp)

    if dry_run:
        print("DRY RUN — ファイルは一切書き込みません。\n")

    preflight()
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    link_dirs(dry_run, backup)
    merge_settings(dry_run, backup)
    merge_mcp(dry_run)

    print("")
    if dry_run:
        print("dry-run 完了。適用するには --dry-run なしで再実行してください。")
    else:
        if backup.used:
            print(f"置換したファイルのバックアップ: {backup.root}")
        print(f"完了。設定を {CLAUDE_DIR} にインストールしました。")


if __name__ == "__main__":
    main()
