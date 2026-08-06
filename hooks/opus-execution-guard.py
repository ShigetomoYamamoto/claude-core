#!/usr/bin/env python3
"""PreToolUse: メインループが思考ティアモデル(Opus / Fable / Mythos)にエスカレーション中、
Edit/Write/変更系 Bash を実行しようとするのをブロックする。

既定は Sonnet 主ループ(role-separation.md)。本 hook は、稀なエスカレーション時に
「判断が終わったら実行は Sonnet へ戻す」規律を機械的に強制する安全網であり、
判定ロジック自体は Opus 主ループ前提だった頃と不変(ADR-024)。

サブエージェント(agent_id あり)・Sonnet/Haiku・監視対象外ツールは通過させる。
判定不能(transcript 読み取り失敗等)は fail-open(ADR-006)。
rules/role-separation.md / ADR-016 / ADR-020 / ADR-024 参照。
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

# リダイレクト検出は _MUTATING から分離する。クォート内を除去してから判定することで
# grep "a->b" / awk 'NR>=600' のような読み取り専用コマンドの誤検知を防ぐ。
# 併せて fd 複製(2>&1)は除外し、fd 付きリダイレクト(1> file)は検出する。
# 注: クォートで囲まれていない `x>1` のような比較はシェルのトークン化なしには
# リダイレクトと区別できず、依然としてブロック側に倒れる(既知の近似・ADR-006 の fail-open 方針とは別問題)。
# /dev/null への書き捨ては副作用がないため除外する(2>/dev/null / cmd > /dev/null が頻出するため)。
_QUOTED = re.compile(r'"[^"]*"' + r"|'[^']*'")
_REDIRECT = re.compile(r'(?<![-=<>&])>>?(?![&=>])(?!\s*/dev/null\b)')


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


THINKING_MODEL_PREFIXES = ("claude-opus-", "claude-fable-", "claude-mythos-")


def is_thinking_model(model):
    return model.lower().startswith(THINKING_MODEL_PREFIXES)


def is_mutating_bash(cmd):
    if _MUTATING.search(cmd):
        return True
    # クォート内は空白に置換する(引用符をまたいだ誤結合を避けるため削除ではなく空白)
    return bool(_REDIRECT.search(_QUOTED.sub(' ', cmd)))


try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    if tool not in EDIT_TOOLS and tool != "Bash":
        sys.exit(0)
    if data.get("agent_id"):
        sys.exit(0)
    model = read_latest_model(data.get("transcript_path", ""))
    if not model or not is_thinking_model(model):
        sys.exit(0)
    if tool in EDIT_TOOLS or (tool == "Bash" and is_mutating_bash(data.get("tool_input", {}).get("command", ""))):
        print("思考ティア(Opus/Fable)はエスカレーション専用で、ファイル編集・変更系 Bash を直接実行できません。", file=sys.stderr)
        print("→ Sonnet サブエージェントに委譲してください(Agent ツール, model: sonnet)。", file=sys.stderr)
        print("  委譲時は run_in_background: false を指定し、完了報告を受け取ってから次へ進むこと(既定は背景実行のためループが止まる)。", file=sys.stderr)
        print("ユーザーにモデル切り替えを依頼しないこと。委譲はあなたが今すぐ自分で実行できる。", file=sys.stderr)
        print("参照: rules/role-separation.md / ADR-016 / ADR-020 / ADR-024", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
except SystemExit:
    raise
except Exception:
    sys.exit(0)
