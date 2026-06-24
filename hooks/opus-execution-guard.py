#!/usr/bin/env python3
"""PreToolUse: メインループの Opus が Edit/Write/変更系 Bash を実行するのをブロックする。

サブエージェント(agent_id あり)・Sonnet/Haiku・監視対象外ツールは通過させる。
判定不能(transcript 読み取り失敗等)は fail-open(ADR-006)。
rules/role-separation.md / ADR-016 参照。
"""
import json, os, sys, re

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_B = r'(?:^|&&|\|\||;|\||\n)\s*'  # コマンド境界
_MUTATING = re.compile(
    rf'{_B}(?:rm|rmdir|unlink|shred|truncate|dd|mv|cp|tee|mkdir|touch)\b'
    rf'|{_B}sed\s+(?:\S+\s+)*-[a-zA-Z]*i[a-zA-Z]*\b'
    rf'|{_B}perl\s+(?:\S+\s+)*-[a-zA-Z]*i[a-zA-Z]*\b'
    rf'|{_B}git\s+(?:add|commit|push|reset|clean|checkout|restore|rm|mv)\b'
    rf'|{_B}(?:npm\s+(?:install|i|ci)|yarn\s+(?:add|install)|pnpm\s+(?:add|install)|pip3?\s+install)\b'
    r'|(?<![&\d])>>?(?!&)',   # リダイレクト > / >> (fd 複製除外)
    re.MULTILINE,
)


def read_latest_model(path):
    """transcript 末尾から直近 assistant の model を返す。失敗時は None。"""
    if not path:
        return None
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if size > 65536:
                f.seek(size - 65536)
            text = f.read()
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "assistant":
            m = obj.get("message", {}).get("model")
            if m:
                return m
    return None


def is_opus(model):
    return model.lower().startswith("claude-opus-")


def is_mutating_bash(cmd):
    return bool(_MUTATING.search(cmd))


try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    if tool not in EDIT_TOOLS and tool != "Bash":
        sys.exit(0)
    if data.get("agent_id"):
        sys.exit(0)
    model = read_latest_model(data.get("transcript_path", ""))
    if not model or not is_opus(model):
        sys.exit(0)
    if tool in EDIT_TOOLS or (tool == "Bash" and is_mutating_bash(data.get("tool_input", {}).get("command", ""))):
        print("Opus はファイル編集・変更系 Bash 操作を直接実行できません。", file=sys.stderr)
        print("`/model sonnet` に切り替えるか、Sonnet サブエージェントに委譲してください。", file=sys.stderr)
        print("参照: rules/role-separation.md / ADR-016", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
except SystemExit:
    raise
except Exception:
    sys.exit(0)
