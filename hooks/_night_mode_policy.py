"""night-mode-guard の判定本体(純関数。I/O は呼び出し側が注入する)。

マーカー `~/.claude/night-mode.json` の契約と、夜の間に止めるものの一覧は ADR-036。
"""
import json
import os
import re
from datetime import datetime

from _night_mode_bash import check_bash

_FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_LOCAL_SERVERS = ("unityMCP", "ccd_session_mgmt", "ccd_turn", "ccd_view", "ccd_sidebar", "ccd_window",
                  "ccd_host", "ccd_directory", "ccd_connectors", "ccd_settings", "visualize",
                  "Claude_Code_iOS_Simulator", "scheduled-tasks")
_SERVICE_PREFIXES = {"slack", "notion", "api", "gmail", "calendar", "drive", "browser"}
_READ_VERBS = {"get", "list", "read", "search", "fetch", "query", "view", "find", "retrieve",
               "download", "whoami", "describe"}
# 先頭が読み取り語でも、こちらが1語でも含まれれば書き込みとみなす(例: get_or_create)。
_WRITE_VERBS = {"create", "update", "delete", "send", "post", "patch", "write", "move", "trash", "share",
                "modify", "append", "add", "remove", "set", "push", "merge", "forward", "reply",
                "schedule", "put", "upload", "edit", "insert", "run", "execute", "navigate", "click",
                "duplicate", "restore", "archive", "publish", "invite"}
_EXPLICIT_READ = {"API-post-search"}


def is_night_on(text, now):
    """マーカーの本文(読めなければ None)と現在時刻(tz つき)から、夜間モードが ON か。

    読めない・JSON でない・オブジェクトでない・until が無い/tz なし/日時でない → ON(閉じる側)。
    """
    try:
        data = json.loads(text)
        until = datetime.fromisoformat(str(data["until"]).replace("Z", "+00:00"))
        if until.tzinfo is None or until.utcoffset() is None:
            return True
        return now < until
    except Exception:
        return True


def until_text(text):
    """メッセージ表示用の until 文字列(取れなければ「不明」)。"""
    try:
        return str(json.loads(text)["until"])
    except Exception:
        return "不明(マーカーが読めない・壊れているため、安全側で ON 扱い)"


def check_file(path, marker, home, cwd=None):
    """Edit/Write 系の対象パスが保護対象なら理由を返す。"""
    if not path:
        return None
    p = os.path.expanduser(str(path))
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    real = os.path.realpath(p)
    if real == os.path.realpath(marker):
        return "夜間モードのマーカーファイルの編集"
    if re.search(r"/\.claude/settings(?:\.local)?\.json$", real):
        return "Claude Code の設定ファイル(settings.json / settings.local.json)の編集"
    if real.startswith(os.path.realpath(os.path.join(home, ".claude", "hooks")) + os.sep):
        return "~/.claude/hooks/ 配下の安全装置の編集"
    return None


def _is_read_name(base):
    if base in _EXPLICIT_READ:
        return True
    toks = [t for t in re.split(r"[-_]", base.lower()) if t]
    if not toks or _WRITE_VERBS & set(toks):
        return False
    idx = 1 if toks[0] in _SERVICE_PREFIXES and len(toks) > 1 else 0
    return toks[idx] in _READ_VERBS


def check_mcp(tool_name, tool_input):
    parts = tool_name.split("__")
    server, base = (parts[1] if len(parts) > 2 else ""), parts[-1]
    if server == "ccd_session":
        target = str((tool_input or {}).get("target", "")).lower()
        if base == "move_to_cloud" or (base == "start_session" and target in ("cloud", "ssh")):
            return f"セッションを外へ移す操作({tool_name})"
        return None
    if server == "ccd_pr":
        return f"PR の自動マージ設定({tool_name})" if base == "set_auto_merge" else None
    if server.startswith(_LOCAL_SERVERS):
        return None
    if _is_read_name(base):
        return None
    return f"外部サービスへの書き込みか操作の疑い({tool_name})"


def check_tool(tool_name, tool_input, marker, home, cwd=None):
    """夜間モード ON のとき、この呼び出しを止める理由(止めなければ None)。"""
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Bash":
        return check_bash(str(tool_input.get("command", "")))
    if tool_name in _FILE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        return check_file(path, marker, home, cwd)
    if tool_name.startswith("mcp__"):
        return check_mcp(tool_name, tool_input)
    return None
