#!/usr/bin/env python3
"""PreToolUse(Bash): 再帰削除(rm -r)・大量削除を検知し、実行前に人間へ諾否を確認する。

二層モデル(ADR-014 / loop-safety「物理層」)— 不可逆操作の最終判断は人間(不変条件4):
- ルート/システム/ホーム相当(/ , /* , "/" , ~ , $HOME , /usr のような単一階層の絶対パス等)への
  再帰削除は決定的ブロック(exit 2)= サーキットブレーカ。
- それ以外の再帰削除(rm -r / -rf / -fr / -fR / --recursive、フラグ分離・大文字も対象)、および
  ワイルドカード削除が THRESHOLD 件以上は permissionDecision="ask" を返し、実行前に確認させる。
- ask は default/auto/acceptEdits/plan/bypass で確認を強制。人間不在(dontAsk/自走ヘッドレス)では
  deny 扱いで止まる(fail-closed = 人間がいなければ不可逆は実行しない、で正しい)。
- 例外(緩和): 再生成可能な許可リスト(SAFE_BASENAMES / セッション scratchpad / $TMPDIR 配下)のみを
  対象とする再帰・ワイルドカード削除は ask を省略する。破滅的ターゲット判定は常に優先。
git 操作の不可逆ブロックは git-destructive-blocker.py が担う。

検出は単一正規表現でなくトークン解析で行う(`rm` 語の確実な要求・フラグ集合の判定)。
これは「rm を要求しない枝で誤検出」「分離フラグ -r -f の取りこぼし」を避けるため。
"""
import json, sys, re, glob, os

THRESHOLD = 10  # この件数以上のワイルドカード削除で確認を促す
SEP = re.compile(r'&&|\|\||[;|&\n]')  # シェルのコマンド区切り

# 「再生成可能」とみなし ask なしで通す許可リスト(基準は明示的リスト — 判断根拠を監査可能に保つ)。
# 破滅的ターゲット判定(パス1)はこのリストより常に優先される。
SAFE_BASENAMES = {
    'node_modules', 'dist', 'build', 'out',
    '.next', '.nuxt', '.cache', '__pycache__',
    '.pytest_cache', 'coverage', 'tmp',
}
SAFE_PATH_PREFIXES = ('/private/tmp/claude-', '/tmp/claude-')  # セッション scratchpad


def ask(reason):
    """実行前に人間へ確認プロンプトを出す(PreToolUse permissionDecision=ask)。"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def deny(message):
    """決定的ブロック(サーキットブレーカ)。"""
    print(message, file=sys.stderr)
    sys.exit(2)


def unquote(tok):
    return tok.strip().strip('"').strip("'")


def is_recursive(flags):
    """フラグ集合が再帰削除(-r / -R / --recursive、分離・連結・大文字いずれも)を含むか。"""
    for f in flags:
        if f == '--recursive':
            return True
        if re.fullmatch(r'-[A-Za-z]+', f) and ('r' in f[1:].lower()):
            return True
    return False


def is_catastrophic(tok):
    """ルート/システム/ホーム相当の破滅的ターゲットか。"""
    t = unquote(tok)
    if t != '/':
        t = t.rstrip('/')
    home_roots = ('~', '$HOME', '${HOME}')
    if t in ('', '/', '/*'):
        return True
    if t in home_roots or t in tuple(h + '/*' for h in home_roots):
        return True
    # 単一階層の絶対パス(/usr, /etc, /home, /Users, /usr/* など)
    if re.fullmatch(r'/[^/]+/?\*?', t):
        return True
    return False


def expand_path(tok, cwd):
    """クォート・環境変数・~ を展開し、cwd 基準の絶対 realpath にする。"""
    t = os.path.expanduser(os.path.expandvars(unquote(tok)))
    if not os.path.isabs(t):
        t = os.path.join(cwd, t)
    return os.path.realpath(t)


def is_safe_target(tok, cwd):
    """再生成可能パス(許可リスト)か。破滅的トークンは常に False。"""
    raw = unquote(tok)
    path = expand_path(raw, cwd)
    if is_catastrophic(raw) or is_catastrophic(path):
        return False
    base = os.path.basename(path.rstrip('/'))
    if any(c in base for c in '*?['):  # dist/* のような glob は親ディレクトリ名で判定
        base = os.path.basename(os.path.dirname(path.rstrip('/')))
    if base in SAFE_BASENAMES:
        return True
    if path.startswith(SAFE_PATH_PREFIXES):
        return True
    tmpdir = os.environ.get('TMPDIR')
    if tmpdir and path.startswith(os.path.realpath(tmpdir).rstrip('/') + os.sep):
        return True
    return False


def parse_rm_segments(cmd):
    """コマンドを区切りで分割し、各 rm 呼び出しの (flags, targets) を返す。"""
    out = []
    for seg in SEP.split(cmd):
        toks = seg.split()
        rm_idx = next((i for i, t in enumerate(toks) if t == 'rm' or t.endswith('/rm')), None)
        if rm_idx is None:
            continue
        args = [a for a in toks[rm_idx + 1:] if a != '--']
        flags = [a for a in args if a.startswith('-')]
        targets = [a for a in args if not a.startswith('-')]
        out.append((flags, targets))
    return out


try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    if not cmd:
        sys.exit(0)

    cwd = data.get('cwd') or os.getcwd()

    rm_calls = parse_rm_segments(cmd)

    # パス1: 破滅的ターゲットへの再帰削除 → 即ブロック(他より優先)
    for flags, targets in rm_calls:
        if is_recursive(flags) and any(is_catastrophic(t) for t in targets):
            deny(f'🔴 rm -r でルート/システム/ホーム相当を削除しようとしました。\nコマンド: {cmd}')

    # パス2: それ以外の再帰削除 → 実行前に確認(全ターゲットが再生成可能なら確認不要)
    for flags, targets in rm_calls:
        if is_recursive(flags):
            if targets and all(is_safe_target(t, cwd) for t in targets):
                continue
            ask(f'再帰削除(rm -r)を検出しました(削除は取り消せません)。実行してよいか確認してください。\nコマンド: {cmd}')

    # パス3: 非再帰でもワイルドカードで大量削除 → 実行前に確認
    for flags, targets in rm_calls:
        for t in targets:
            if '*' in t and not is_safe_target(t, cwd):
                try:
                    matches = glob.glob(unquote(t), recursive=True)
                except Exception:
                    matches = []
                if len(matches) >= THRESHOLD:
                    sample = '\n'.join(f'  - {m}' for m in matches[:10])
                    ask(
                        f'rm のワイルドカード削除: {len(matches)} 件が対象です(取り消せません)。'
                        f'実行してよいか確認してください。\nパターン: {t}\n最初の10件:\n{sample}'
                    )

except SystemExit:
    raise
except Exception:
    sys.exit(0)
