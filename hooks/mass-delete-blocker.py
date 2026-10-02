#!/usr/bin/env python3
"""PreToolUse(Bash): 再帰削除(rm -r)・大量削除を検知し、実行前に人間へ諾否を確認する。

二層モデル(ADR-014 / loop-safety「物理層」)— 不可逆操作の最終判断は人間(不変条件4):
- ルート/システム/ホーム相当(/ , /* , "/" , ~ , $HOME , 展開済みのホーム絶対パス ,
  /usr のような単一階層の絶対パス等)への再帰削除は決定的ブロック(exit 2)= サーキットブレーカ。
  判定は生のトークンと展開後の絶対パスの両方に対して行う。
- それ以外の再帰削除(rm -r / -rf / -fr / -fR / --recursive、フラグ分離・大文字も対象)、および
  ワイルドカード削除が THRESHOLD 件以上は permissionDecision="ask" を返し、実行前に確認させる。
- ask は default/auto/acceptEdits/plan/bypass で確認を強制。人間不在(dontAsk/自走ヘッドレス)では
  deny 扱いで止まる(fail-closed = 人間がいなければ不可逆は実行しない、で正しい)。
- 例外(緩和): 再生成可能な許可リスト(SAFE_BASENAMES / セッション scratchpad / $TMPDIR 配下)のみを
  対象とする再帰・ワイルドカード削除は ask を省略する。破滅的ターゲット判定は常に優先。

find / xargs 経由の削除も検出する:
- `find ... -delete` / `find ... -exec|-execdir|-ok|-okdir rm ...`: 起点パスが破滅的なら deny、
  起点が全て再生成可能なら ask を省略、それ以外は ask。
- `find -exec|-execdir|-ok|-okdir` は rm / unlink / rmdir / shred のいずれかを実行する形を対象とする。
- `xargs [opts] rm|unlink|rmdir|shred ...`: 対象が stdin から来て判定できないため、-r の有無を問わず常に ask。
- `sh -c "..."` に隠れた形は ask のみ(deny しない)。

rm トークンを使わない削除コマンドも検出する(#109 / ADR-028):
- `unlink` / `rmdir`: 常に ask(for / if / do / ( 等の構文の直後もコマンド位置とみなす)。対象が1つ以上あり全て再生成可能(自身か、cwd 配下での祖先ディレクトリが許可リスト)なら省略。
- `shred`: 常に ask(緩和なし。-u が無くても中身を破壊するため)。
- `rsync` は delete 系オプション(`--delete` / `--del` / `--delete-*`)があるときだけ対象。
  dry-run(`--dry-run` / `-n` を含む短縮クラスタ)は対象外。宛先 = 最後の非オプショントークン。
  宛先がルート/ホーム相当なら deny、再生成可能なら通過、それ以外は ask。
  リモート宛先(`host:path`)は判定不能なので常に ask(コロン以降のパスが破滅的なら deny)。
  `--remove-source-files` は mv 相当として対象外。
  値を別トークンで取るオプション(`--exclude X` / `-e ssh` 等)の値は宛先として数えない。
- いずれも `sh -c` に隠れた形は ask のみ(deny しない)。

インタプリタ経由の削除(`python3 -c "os.remove(...)"`)と `sh -c` に隠れた rm も、
呼び出し形式と既知 API の同時出現で近似検出する(#100 / ADR-028)。文字列から効果を
確定することはできないため、この網は意図的に不完全である。
git 操作の不可逆ブロック(reset --hard / clean -fd / push --force 等)は claude-engineering 側の
git-destructive-blocker.py が担う。core には無い — git は開発専用であり core(ドメイン中立)の射程外。

検出は単一正規表現でなくトークン解析で行う(`rm` 語の確実な要求・フラグ集合の判定)。
これは「rm を要求しない枝で誤検出」「分離フラグ -r -f の取りこぼし」を避けるため。
"""
import json, sys, re, glob, os

# hook は毎回のツール呼び出しで起動する。~/.claude/hooks/ に __pycache__ を作ると
# installer の verify が UNKNOWN として拾ってしまうため、バイトコードを書かせない。
sys.dont_write_bytecode = True

# 共有ヘルパ(ADR-028)。欠けても従来の rm トークン解析のみで動作を続ける。
try:
    from _command_effects import DELETE_APIS, has_inline_code, has_inline_shell, unquote_all
except Exception:                                    # pragma: no cover
    DELETE_APIS = None
    has_inline_code = has_inline_shell = lambda cmd: False
    unquote_all = lambda cmd: cmd

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
_HOME = os.path.realpath(os.path.expanduser('~'))  # 展開済みのホーム絶対パス


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
    # 展開済みのホーム絶対パス(/Users/<user>)もホーム相当として扱う。エージェントは `~` では
    # なく展開済みの絶対パスでコマンドを組み立てることが多く、リテラルの `~` だけを見ていると
    # ホームごと削除する指定が ask 止まりになっていた。ホーム直下の個別ディレクトリ
    # (~/Downloads 等)は対象外 — 完全一致とその直下 glob だけを破滅的とみなす。
    if t == _HOME or t == _HOME + '/*':
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


FIND_ACTIONS = ('-exec', '-execdir', '-ok', '-okdir')
DELETE_CMDS = ('rm', 'unlink', 'rmdir', 'shred')  # find -exec / xargs が実行したら削除とみなす
FIND_START_STOPS = ('(', '\\(', '!', ')')
XARGS_ARG_OPTS = ('-I', '-n', '-P', '-L', '-s', '-d', '-E', '-a')


def _is_cmd(tok, name):
    return tok == name or tok.endswith('/' + name)


def parse_find_calls(cmd):
    """find による削除(-delete / -exec|-execdir|-ok|-okdir rm)ごとの起点パス一覧を返す。"""
    out = []
    for seg in SEP.split(cmd):
        toks = seg.split()
        idx = next((i for i, t in enumerate(toks) if _is_cmd(t, 'find')), None)
        if idx is None:
            continue
        rest = toks[idx + 1:]
        deletes = '-delete' in rest or any(
            t in FIND_ACTIONS and i + 1 < len(rest) and any(_is_cmd(rest[i + 1], c) for c in DELETE_CMDS)
            for i, t in enumerate(rest)
        )
        if not deletes:
            continue
        i = 0
        while i < len(rest) and rest[i] in ('-H', '-L', '-P'):
            i += 1
        starts = []
        while i < len(rest) and not rest[i].startswith('-') and rest[i] not in FIND_START_STOPS:
            starts.append(rest[i])
            i += 1
        out.append(starts or ['.'])
    return out


def has_xargs_rm(cmd):
    """xargs が削除コマンド(rm / unlink / rmdir / shred)を実行する形を含むか。"""
    for seg in SEP.split(cmd):
        toks = seg.split()
        for idx, t in enumerate(toks):
            if not _is_cmd(t, 'xargs'):
                continue
            i = idx + 1
            while i < len(toks) and toks[i].startswith('-'):
                i += 2 if toks[i] in XARGS_ARG_OPTS else 1
            if i < len(toks) and any(_is_cmd(toks[i], c) for c in DELETE_CMDS):
                return True
    return False


# コマンド位置に至るまでの前置きとして許す語(env 代入・ラッパ・sh -c のシェル名とフラグ)。
# `echo unlink` や `grep -rn unlink` の引数としての出現を、コマンドと誤認しないために使う。
CMD_PREFIX_WORDS = (
    'sudo', 'command', 'exec', 'nohup', 'time', 'env', 'nice',
    'if', 'then', 'else', 'elif', 'do', 'while', 'until', '{', '(', '!',
)
SHELL_NAMES = ('sh', 'bash', 'zsh', 'dash', 'ksh')


def _cmd_idx(toks, name):
    """toks のうち name がコマンド位置にある index(無ければ None)。"""
    toks = [t.lstrip('({') or t for t in toks]  # `(unlink` / `{shred` をコマンドとして見る
    for i, t in enumerate(toks):
        if _is_cmd(t, name):
            ok = all(
                '=' in p or p in CMD_PREFIX_WORDS or p.startswith('-')
                or any(_is_cmd(p, sh) for sh in SHELL_NAMES)
                for p in toks[:i]
            )
            return i if ok else None
    return None


def parse_simple_delete_calls(cmd):
    """unlink / rmdir / shred の呼び出しごとに (名前, 非オプション対象一覧) を返す。"""
    out = []
    for seg in SEP.split(cmd):
        toks = seg.split()
        for name in ('unlink', 'rmdir', 'shred'):
            idx = _cmd_idx(toks, name)
            if idx is None:
                continue
            args = [a for a in toks[idx + 1:] if a != '--']
            out.append((name, [a.rstrip(')}') or a for a in args if not a.startswith('-')]))
    return out


RSYNC_ARG_OPTS = frozenset("""-e --rsh -f --filter --exclude --include --exclude-from --include-from
--files-from -T --temp-dir --backup-dir --suffix --link-dest --compare-dest --copy-dest --partial-dir
--log-file --chmod --chown --password-file --port --timeout --contimeout --max-delete --max-size
--min-size --bwlimit -B --block-size -M --remote-option --out-format --info --debug --usermap
--groupmap --iconv --modify-window --sockopts --address --protocol --outbuf --checksum-choice
--compress-choice --compress-level --skip-compress""".split())  # 値を別トークンで取るオプション


def rsync_operands(rest):
    """オプションと、その別トークンの値を読み飛ばした非オプショントークン一覧。"""
    out = []
    i = 0
    while i < len(rest):
        t = rest[i]
        if t.startswith('-'):
            i += 2 if t in RSYNC_ARG_OPTS else 1
            continue
        out.append(t)
        i += 1
    return out


def is_rsync_delete_opt(tok):
    return tok in ('--delete', '--del') or tok.startswith('--delete-')


def is_rsync_dry_run(tok):
    return tok == '--dry-run' or (re.fullmatch(r'-[A-Za-z]+', tok) is not None and 'n' in tok[1:])


def parse_rsync_delete_dests(cmd):
    """delete 系オプション付き・dry-run でない rsync ごとの宛先(最後の非オプショントークン)を返す。"""
    out = []
    for seg in SEP.split(cmd):
        toks = seg.split()
        idx = _cmd_idx(toks, 'rsync')
        if idx is None:
            continue
        rest = toks[idx + 1:]
        if not any(is_rsync_delete_opt(t) for t in rest) or any(is_rsync_dry_run(t) for t in rest):
            continue
        operands = rsync_operands(rest)
        if len(operands) < 2:
            continue
        out.append(operands[-1])
    return out


def rsync_dest_verdict(dest, cwd):
    """rsync --delete の宛先を 'deny' / 'pass' / 'ask' に分類する。"""
    d = unquote(dest)
    if ':' in d and not d.startswith('/'):  # リモート host:path。パスは判定できないので通過はない
        return 'deny' if is_catastrophic(d.split(':', 1)[1]) else 'ask'
    if is_catastrophic(d) or is_catastrophic(expand_path(d, cwd)):
        return 'deny'
    return 'pass' if is_safe_target(d, cwd) else 'ask'


def is_safe_entry(tok, cwd):
    """unlink / rmdir 用: 自身が再生成可能、またはその配下(祖先ディレクトリが許可リスト)か。"""
    if is_safe_target(tok, cwd):
        return True
    path = expand_path(tok, cwd)
    if is_catastrophic(path):
        return False
    # 祖先ルールは cwd 配下のパスにだけ適用する(~/work/out/ 配下のリポジトリ等を巻き込まない)。
    rel = os.path.relpath(path, os.path.realpath(cwd))
    if rel == '..' or rel.startswith('..' + os.sep):
        return False
    return any(part in SAFE_BASENAMES for part in rel.split(os.sep)[:-1])


def simple_delete_ask_name(cmd, cwd):
    """unlink / rmdir / shred / rsync --delete のうち確認が要る最初のコマンド名(無ければ None)。"""
    for name, targets in parse_simple_delete_calls(cmd):
        if name == 'shred':
            return name
        if not (targets and all(is_safe_entry(t, cwd) for t in targets)):
            return name
    for dest in parse_rsync_delete_dests(cmd):
        if rsync_dest_verdict(dest, cwd) != 'pass':
            return 'rsync --delete'
    return None


FIND_ASK_MSG = 'find / xargs 経由の削除を検出しました(削除は取り消せません)。実行してよいか確認してください。\nコマンド: {cmd}'
DELETE_ASK_MSG = '{name} による削除を検出しました(削除は取り消せません)。実行してよいか確認してください。\nコマンド: {cmd}'

try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    if not cmd:
        sys.exit(0)

    cwd = data.get('cwd') or os.getcwd()

    rm_calls = parse_rm_segments(cmd)

    # パス1: 破滅的ターゲットへの再帰削除 → 即ブロック(他より優先)
    for flags, targets in rm_calls:
        # 生のトークンと展開後の絶対パスの両方で判定する。`cd /Users/x && rm -rf .` や
        # `rm -rf ../..` のように、相対指定でホーム/システムへ到達する経路を取りこぼさないため
        # (is_safe_target は以前から両方を見ており、パス1だけが生トークンのみだった)。
        if is_recursive(flags) and any(
            is_catastrophic(t) or is_catastrophic(expand_path(t, cwd)) for t in targets
        ):
            deny(f'🔴 rm -r でルート/システム/ホーム相当を削除しようとしました。\nコマンド: {cmd}')

    # パス1(find): find の起点が破滅的なら即ブロック。素の解析のみ(ADR-028)。
    find_calls = parse_find_calls(cmd)
    for starts in find_calls:
        if any(is_catastrophic(t) or is_catastrophic(expand_path(t, cwd)) for t in starts):
            deny(f'🔴 find でルート/システム/ホーム相当を起点に削除しようとしました。\nコマンド: {cmd}')

    # パス1(rsync): delete 系オプション付き rsync の宛先がルート/ホーム相当なら即ブロック。素の解析のみ。
    for dest in parse_rsync_delete_dests(cmd):
        if rsync_dest_verdict(dest, cwd) == 'deny':
            deny(f'🔴 rsync --delete でルート/システム/ホーム相当を宛先に削除しようとしました。\nコマンド: {cmd}')

    # パス1.5: インタプリタ経由の削除(python3 -c "import os; os.remove(...)" 等)。
    # rm 拒否ルールをブロックされた後、別経路で同じ削除が実行された事例への対応(#100)。
    # 呼び出し形式と既知の削除 API の同時出現による近似であり、未知の手段は素通りする(ADR-028)。
    if DELETE_APIS is not None and has_inline_code(cmd) and DELETE_APIS.search(cmd):
        ask(f'インタプリタ経由の削除操作を検出しました(取り消せません)。実行してよいか確認してください。\nコマンド: {cmd}')

    # sh -c "rm -rf x" のようにクォート内へ隠れた rm は素のトークン解析に載らない。
    # 呼び出し形式が sh -c のときだけクォートを外した写しも解析対象に足す。
    # 破滅的ターゲット判定(パス1 = 決定的ブロック)は誤ブロックを避けるため素の解析のみに留める(ADR-028)。
    if has_inline_shell(cmd):
        rm_calls = rm_calls + parse_rm_segments(unquote_all(cmd))

    # パス1.8: find / xargs 経由の削除 → 確認(find は起点が全て再生成可能なら省略、xargs は常に確認)。
    # sh -c に隠れた形は unquote_all の写しも見るが ask のみ(deny しない)。
    if has_inline_shell(cmd):
        find_calls = find_calls + parse_find_calls(unquote_all(cmd))
    xargs_rm = has_xargs_rm(cmd) or (has_inline_shell(cmd) and has_xargs_rm(unquote_all(cmd)))
    if xargs_rm or any(not all(is_safe_target(t, cwd) for t in starts) for starts in find_calls):
        ask(FIND_ASK_MSG.format(cmd=cmd))

    # パス1.8(続き): unlink / rmdir / shred / rsync --delete。sh -c に隠れた写しも見るが ask のみ。
    simple_name = simple_delete_ask_name(cmd, cwd) or (
        simple_delete_ask_name(unquote_all(cmd), cwd) if has_inline_shell(cmd) else None
    )
    if simple_name:
        ask(DELETE_ASK_MSG.format(name=simple_name, cmd=cmd))

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
