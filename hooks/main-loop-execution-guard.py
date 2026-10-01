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
- 例外パスへのリダイレクトのみで構成される Bash — 同じ2パス(#103 / ADR-028)
判定不能時(パスが取れない等)は fail-open(ADR-006)。
rules/role-separation.md / ADR-026 参照。
"""
import json, os, sys, re

# hook は毎回のツール呼び出しで起動する。~/.claude/hooks/ に __pycache__ を作ると
# installer の verify が UNKNOWN として拾ってしまうため、バイトコードを書かせない。
sys.dont_write_bytecode = True

# 共有ヘルパ(ADR-028)。欠けても従来の検出のみで動作を続ける(ADR-006 の fail-open と同じ判断)。
try:
    from _command_effects import (
        DELETE_APIS, WRITE_APIS, has_inline_code, has_inline_shell, unquote_all,
    )
except Exception:                                    # pragma: no cover
    DELETE_APIS = WRITE_APIS = None
    has_inline_code = has_inline_shell = lambda cmd: False
    unquote_all = lambda cmd: cmd

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_B = r'(?:^|&&|\|\||;|\||\n)\s*'  # コマンド境界
_MUTATING = re.compile(
    rf'{_B}(?:rm|rmdir|unlink|shred|truncate|dd|mv|cp|tee|mkdir|touch)\b'
    # sed/perl の -i は「同じコマンド区間内」だけを探す。引数トークンは [^\s;|&]+ で区切り記号を
    # またがせず、後続コマンド(; grep -i 等)のフラグを拾わない。バックスラッシュ改行の継続だけは辿る。
    rf'|{_B}sed(?:(?:[ \t]|\\\n)+[^\s;|&]+)*(?:[ \t]|\\\n)+-[a-zA-Z]*i[a-zA-Z]*\b'
    rf'|{_B}perl(?:(?:[ \t]|\\\n)+[^\s;|&]+)*(?:[ \t]|\\\n)+-[a-zA-Z]*i[a-zA-Z]*\b'
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

# リダイレクト先の取り出し。_REDIRECT と同じ先読み/後読みだが /dev/null も拾う
# (例外パス判定側で読み飛ばすため)。
_REDIR_TARGET = re.compile(r'(?<![-=<>&])>>?(?![&=>])\s*([^\s;|&]+)')


def is_mutating_bash(cmd):
    # クォート内は先に空白へ置換し、その結果に両方の判定をかける。
    # 引用符の中の | や ; はシェルの区切りではなくただの文字だが、正規表現には
    # 区別がつかない(grep "cp\|mv" のような読み取り専用コマンドが誤検知される)。
    # 空白に置換するのは、引用符をまたいだ誤結合を避けるため(削除ではなく空白)。
    # 代償: 引用符内に隠れた破壊操作は、この素の判定だけでは見えない。
    # sh -c / インタプリタのインラインコードという「呼び出し形式」が現れた場合に限り
    # 下で別途フォローする(ADR-028)。形式が現れない難読化(変数組み立て・base64 経由等)は
    # 引き続き素通りする — この網は意図的に不完全である。
    stripped = _QUOTED.sub(' ', cmd)
    if _MUTATING.search(stripped):
        return True
    # クォート内に隠れたシェルコマンド(sh -c "...; rm -rf x")は素の判定に載らない。
    # 呼び出し形式が sh -c のときだけクォートを外した写しでも判定する(ADR-028)。
    if has_inline_shell(cmd) and _MUTATING.search(unquote_all(cmd)):
        return True
    # インタプリタへのインラインコード経由の書き込み/削除(python3 -c "os.remove(...)")。
    # 呼び出し形式と既知 API の同時出現による近似であり、網羅ではない(ADR-028)。
    if has_inline_code(cmd) and DELETE_APIS is not None and (
        DELETE_APIS.search(cmd) or WRITE_APIS.search(cmd)
    ):
        return True
    return bool(_REDIRECT.search(stripped))


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


def bash_targets_all_allowed(cmd):
    """リダイレクトだけが変更要因で、出力先がすべて例外パスなら True。

    Edit/Write が file_path で例外パスを判定できるのに Bash では判定できず、
    `cat >> ~/.claude/projects/*/memory/MEMORY.md` が弾かれていた件への対応(#103)。
    救うのはリダイレクト先だけに限る。全引数をパスとして解決すると
    `rm -rf ~/.claude/projects/*/memory/` まで通る穴になるため、
    変更系トークンやインラインコードが混ざる場合は常に False。
    相対パスは cwd 依存で誤判定するため通さない(fail-closed)。
    """
    stripped = _QUOTED.sub(' ', cmd)
    if _MUTATING.search(stripped):
        return False
    if has_inline_code(cmd) or has_inline_shell(cmd):
        return False
    targets = _REDIR_TARGET.findall(stripped)
    if not targets:
        return False
    for t in targets:
        if t == '/dev/null':
            continue
        if '$' in t or any(c in t for c in '*?['):
            return False                 # 展開結果が定まらないものは通さない
        if not (t.startswith('/') or t.startswith('~/')):
            return False                 # 相対パスは通さない
        if not is_allowed_path(os.path.expanduser(t)):
            return False
    return True


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
    else:
        command = tool_input.get("command", "")
        if not is_mutating_bash(command):
            sys.exit(0)                  # 読み取り系 Bash は通す
        if bash_targets_all_allowed(command):
            sys.exit(0)                  # 例外パスへのリダイレクトのみ
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
