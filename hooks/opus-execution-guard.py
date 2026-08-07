#!/usr/bin/env python3
"""PreToolUse: メインループ(agent_id なし)による実作業を止め、実行を委譲層へ回させる。

役割分担(rules/role-separation.md): メインは思考・計画・管理に専念し、実作業は
より安価で速い実行層(サブエージェント)が担う。判定軸は「モデル」ではなく
「メインループか実行層か」(ADR-026)。旧実装は思考ティア(Opus/Fable)のときだけ
発火していたため、既定が Sonnet になった後(ADR-024)は実質何も強制していなかった。

通過させるもの:
- サブエージェント(stdin に agent_id あり) — 実行層そのもの
- 監視対象外ツール
- 例外パスへの Edit/Write — auto-memory とセッション scratchpad のみ
判定不能時(パスが取れない等)は fail-open(ADR-006)。
rules/role-separation.md / ADR-026 参照。
"""
import json, os, sys, re

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_B = r'(?:^|&&|\|\||;|\||\n)\s*'  # コマンド境界
_MUTATING = re.compile(
    rf'{_B}(?:rm|rmdir|unlink|shred|truncate|dd|mv|cp|tee|mkdir|touch)\b'
    rf'|{_B}sed\s+(?:\S+\s+)*-[a-zA-Z]*i[a-zA-Z]*\b'
    rf'|{_B}perl\s+(?:\S+\s+)*-[a-zA-Z]*i[a-zA-Z]*\b'
    rf'|{_B}git\s+(?:add|commit|push|reset|clean|checkout|restore|rm|mv)\b'
    rf'|{_B}(?:npm\s+(?:install|i|ci)|yarn\s+(?:add|install)|pnpm\s+(?:add|install)|pip3?\s+install)\b',
    re.MULTILINE,
)

# クォート除去(_QUOTED)は _MUTATING / _REDIRECT の両方の前段で使う。除去してから判定することで
# grep "a->b" / awk 'NR>=600' のような読み取り専用コマンドの誤検知を防ぐ。
# 併せて fd 複製(2>&1)は除外し、fd 付きリダイレクト(1> file)は検出する。
# 注: クォートで囲まれていない `x>1` のような比較はシェルのトークン化なしには
# リダイレクトと区別できず、依然としてブロック側に倒れる(既知の近似・ADR-006 の fail-open 方針とは別問題)。
# /dev/null への書き捨ては副作用がないため除外する(2>/dev/null / cmd > /dev/null が頻出するため)。
_QUOTED = re.compile(r'"[^"]*"' + r"|'[^']*'")
_REDIRECT = re.compile(r'(?<![-=<>&])>>?(?![&=>])(?!\s*/dev/null\b)')


def is_mutating_bash(cmd):
    # クォート内は先に空白へ置換し、その結果に両方の判定をかける。
    # 引用符の中の | や ; はシェルの区切りではなくただの文字だが、正規表現には
    # 区別がつかない(grep "cp\|mv" のような読み取り専用コマンドが誤検知される)。
    # 空白に置換するのは、引用符をまたいだ誤結合を避けるため(削除ではなく空白)。
    # 代償: 引用符内のサブシェル(sh -c "...; rm -rf x")に隠れた破壊操作は検出できなくなる。
    # ヒアドキュメントや python3 -c 経由の書き込みが元々素通りである以上、
    # 検出網を広げるより誤検知を減らす方を優先する(ADR-006 の fail-open と同じ判断)。
    stripped = _QUOTED.sub(' ', cmd)
    return bool(_MUTATING.search(stripped)) or bool(_REDIRECT.search(stripped))


# メインループに許す例外パス。絶対パスが固定で誤分類の余地がないものだけに限る。
# 「設定ファイルかプロダクトコードか」という意味による分類は採らない(ADR-026):
# claude-core のような設定リポジトリでは両者が同一ファイルであり、パスに落とせない。
_MEMORY_ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects")
_SCRATCHPAD = re.compile(r'^/(?:private/)?tmp/claude-[^/]+/.+/scratchpad(?:/|$)')


def is_allowed_path(path):
    """メインループに書き込みを許すパスか。判定できなければ False。"""
    if not path:
        return False
    p = os.path.abspath(path)
    if p.startswith(_MEMORY_ROOT + os.sep) and "/memory/" in p + "/":
        return True
    return bool(_SCRATCHPAD.match(p))


try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    if tool not in EDIT_TOOLS and tool != "Bash":
        sys.exit(0)
    if data.get("agent_id"):
        sys.exit(0)                      # 実行層(サブエージェント)は通す
    tool_input = data.get("tool_input", {})
    if tool in EDIT_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not path:
            sys.exit(0)                  # パス不明は fail-open(ADR-006)
        if is_allowed_path(path):
            sys.exit(0)
    elif not is_mutating_bash(tool_input.get("command", "")):
        sys.exit(0)                      # 読み取り系 Bash は通す
    print("メインループは実作業を担当しません(役割分担・ADR-026)。この操作は実行できません。", file=sys.stderr)
    print("→ 実行はサブエージェントに委譲してください(Agent ツール, model: sonnet 等の実行層)。", file=sys.stderr)
    print("  委譲時は run_in_background: false を指定し、完了報告を受け取ってから次へ進むこと(既定は背景実行のためループが止まる)。", file=sys.stderr)
    print("ユーザーにモデル切り替えを依頼しないこと。委譲はあなたが今すぐ自分で実行できる。", file=sys.stderr)
    print("メインに許される書き込みは auto-memory(~/.claude/projects/*/memory/) とセッション scratchpad のみ。", file=sys.stderr)
    print("参照: rules/role-separation.md / ADR-026", file=sys.stderr)
    sys.exit(2)
except SystemExit:
    raise
except Exception:
    sys.exit(0)
