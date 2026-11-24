#!/usr/bin/env python3
"""PreToolUse(Bash|Edit|Write|MultiEdit|NotebookEdit|mcp__*): 夜間モード中は外に見える操作を止める。

`~/.claude/night-mode.json` があり、until が未来(または読めない)のときだけ働く(ADR-036)。
マーカーが無ければ何もせず即終了する(全セッションの全ツール呼び出しで走るため最初の検査)。
マーカーがある間に限り、判定コード自身の例外もブロックにする(ADR-006 の fail-open とは意図的に逆)。
"""
import os
import sys

sys.dont_write_bytecode = True

HOME = os.path.expanduser("~")
MARKER = os.path.join(HOME, ".claude", "night-mode.json")

if not os.path.lexists(MARKER):
    sys.exit(0)


def block(reason, until):
    sys.stderr.write(
        "夜間モードが ON のため、この操作を止めました。\n"
        f"止めた操作: {reason}\n"
        f"マーカー: {MARKER}(until: {until})\n"
        "夜の作業は、ローカルの作業ブランチまでで止め、push・PR・外への書き込みはしません。\n"
        "早く解除するには、人間が自分のターミナルでこのファイルを削除するか、"
        "`workops night end` を実行してください(エージェントからは実行できません)。\n")
    sys.exit(2)


until = "不明"
try:
    import json
    from datetime import datetime, timezone
    try:
        with open(MARKER, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        text = None
    import _night_mode_policy as policy
    until = policy.until_text(text)
    if not policy.is_night_on(text, datetime.now(timezone.utc)):
        sys.exit(0)
    data = json.load(sys.stdin)
    reason = policy.check_tool(str(data.get("tool_name", "")), data.get("tool_input"),
                               MARKER, HOME, data.get("cwd"))
except SystemExit:
    raise
except Exception as e:
    block(f"判定中にエラーが出たため安全側で停止({type(e).__name__})", until)
if reason:
    block(reason, until)
sys.exit(0)
