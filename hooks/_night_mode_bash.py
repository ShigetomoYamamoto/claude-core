"""night-mode-guard の Bash 判定(純関数のみ・I/O なし)。

コマンド文字列を、クォートを考慮して区切り、各コマンドの先頭語を見る。
`g"it" push` / `\\git push` / `git -C x push` / `sh -c '...'` / `sudo git push` も同じ形に直して判定する。
最後に、先頭のプログラムに関係なく「git の後ろに push」などの語があれば止める網を張る(止めすぎは承知)。
これは検出網であり境界ではない(ADR-028)。curl での POST・スクリプトファイルの中身・
インタプリタ内の subprocess などは、この網にかからない形なら見ない(ADR-036 の限界)。
"""
import os
import posixpath
import re
import shlex

from _night_mode_git import check_gh, check_git
from _night_mode_tamper import check_tamper

_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "csh", "tcsh"}
_GIT_LIKE = {"git", "gh", "git-send-email", "eval"} | _SHELLS
_WRAPPERS = {"command", "builtin", "sudo", "doas", "env", "time", "nohup", "exec", "nice", "xargs",
             "then", "do", "else", "if", "while", "until", "!", "timeout", "stdbuf", "caffeinate",
             "script", "arch", "watch", "flock"}
_MAX_DEPTH = 3
# 環境変数での設定上書き・外部コマンドの仕込み。次の (名前, 値) だけは無害なので通す。
_ENV_ASSIGN = re.compile(r"(?<![\w])((?:GIT_\w*|EDITOR|VISUAL|SSH_ASKPASS|PAGER))=(\S*)")
_SAFE_ENV = {("GIT_EDITOR", "true"), ("GIT_EDITOR", ":"), ("GIT_SEQUENCE_EDITOR", "true"),
             ("GIT_SEQUENCE_EDITOR", ":"), ("EDITOR", "true"), ("EDITOR", ":"), ("VISUAL", "true"),
             ("VISUAL", ":"), ("GIT_PAGER", "cat"), ("PAGER", "cat"), ("GIT_TERMINAL_PROMPT", "0")}
_FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
_REDIR_OP = re.compile(r"\d*(?:<<<|<<-?|<>|<|>>|>\|?|&>)")
_REDIR_ATTACHED = re.compile(r"\d*(?:<<<|<<-?|<|>>|>)\S+")
# 網: 先頭のプログラムに関係なく、語の並びだけで見る(python -c・node -e・osascript・未知のラッパーも)。
_CATCH_GIT = re.compile(r"\bgit\b.*\b(?:push|send-email)\b", re.S)
# 2つ目の網: gh の後ろのどこかに書き込み形の語があれば止める(1つ目の check_gh が見逃す形の保険)。
_CATCH_GH = re.compile(
    r"\bgh\b.*\b(?:pr[^\w-]+(?:create|merge|review|comment|edit|close|reopen|ready)"
    r"|issue[^\w-]+(?:create|comment|edit|close)|release[^\w-]+(?:create|edit|delete|upload)"
    r"|repo[^\w-]+(?:create|fork|delete|edit)|workflow[^\w-]+run)\b", re.S)
_CATCH_GH_API = re.compile(r"\bgh\b.*\bapi\b", re.S)
_CATCH_API_WRITE = re.compile(
    r"(?<![\w-])(?:(?:-x|--method)[=\s]*(?:post|put|patch|delete)\b|-f|--field|--raw-field|--input)")
_GH_WORD = re.compile(r"(?<![\w-])gh(?![\w-])", re.I)
_GH_SPLIT = re.compile(r"[\s,\[\]()]+")
_WORD_SPLIT = re.compile(r"[\s;|&()`<>=]+")


def split_segments(cmd):
    """クォートの外の && || ; | & 改行 ( ) ` と、"..." 内の $( ` でコマンドを区切る。"""
    segs, buf, quote, i = [], [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and quote != "'":
            buf.append(cmd[i:i + 2]); i += 2; continue
        if quote:
            if c == quote:
                quote = None
            elif quote == '"' and (c == "`" or cmd.startswith("$(", i)):
                segs.append("".join(buf)); buf = []; i += 2 if c == "$" else 1; continue
            buf.append(c)
        elif c in "\"'":
            quote = c; buf.append(c)
        elif c in ";|&\n()`":
            segs.append("".join(buf)); buf = []
        else:
            buf.append(c)
        i += 1
    segs.append("".join(buf))
    return [s for s in segs if s.strip()]


def _tokens(seg):
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return re.sub(r"[\"'()`]", " ", seg).replace("\\", "").split()


def _base(tok):
    return tok.rsplit("/", 1)[-1]


def _is_git_word(word):
    base = _base(word).casefold()
    return base in ("git", "gh") or base.startswith("git-")


def _check_env(norm):
    for m in _ENV_ASSIGN.finditer(norm):
        if (m.group(1), m.group(2)) not in _SAFE_ENV:
            return f"git の設定や外部コマンドを環境変数で仕込むコマンド({m.group(1)}=...)"
    return None


def _check_catch_all(norm):
    """先頭のプログラムに関係なく、git の後ろの push / send-email、gh の書き込み形を止める。"""
    text = norm.casefold()
    if _CATCH_GIT.search(text):
        return "git push / send-email の語を含むコマンド(インタプリタや未知のラッパー経由も止める)"
    reason = _check_gh_anywhere(norm)
    if reason:
        return reason
    if _CATCH_GH.search(text):
        return "gh の書き込み形の語を含むコマンド"
    if _CATCH_GH_API.search(text) and _CATCH_API_WRITE.search(text):
        return "gh api の書き込み形の語を含むコマンド"
    return None


def _check_gh_anywhere(norm):
    """`gh` の語の後ろにサブコマンドの語があれば、読み取りの許可リストに合わない限り止める(deny unless read)。"""
    for m in _GH_WORD.finditer(norm):
        words = [w for w in _GH_SPLIT.split(norm[m.end():]) if w]
        words = [w if w.startswith("-") else w.casefold() for w in words]
        reason = check_gh(words)
        if reason:
            return f"{reason}(コマンドのどこかに gh がある場合は、読み取り以外を止める)"
    return None


def _home_path(path, cwd, home):
    p = path
    for pre in ("${HOME}", "$HOME", "~"):
        if p == pre or p.startswith(pre + "/"):
            p = home + p[len(pre):]
            break
    if not posixpath.isabs(p):
        p = posixpath.join(cwd or home, p)
    return posixpath.normpath(p).casefold()


def _check_cd(toks, cwd, home):
    """cd / pushd でホームの .claude に入るのを止める。"""
    if not toks or _base(toks[0]) not in ("cd", "pushd", "chdir"):
        return None
    args = [t for t in toks[1:] if not t.startswith("-")]
    if not args:
        return None
    target = _home_path(args[0], cwd, home)
    protected = posixpath.normpath(posixpath.join(home, ".claude")).casefold()
    if target == protected or target.startswith(protected + "/"):
        return "ホームの .claude への cd / pushd"
    return None


def _shell_script_reason(toks, depth, ctx):
    """シェル呼び出しの判定。-c の中身は再帰、標準入力から読む形・実行ファイルが不明な形は止める。"""
    args = toks[1:]
    if any(a in ("--version", "--help") for a in args):
        return None
    script, has_c, stdin_s, files = None, False, False, []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-o", "+o", "-O", "+O", "--rcfile", "--init-file"):
            i += 2; continue
        if a.startswith(("--rcfile=", "--init-file=")):
            i += 1; continue
        if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", a) and script is None and not has_c:
            has_c = True
            j = i + 1
            while j < len(args) and args[j].startswith("-"):
                j += 1
            script = args[j] if j < len(args) else None
            i = j + 1
            continue
        if _REDIR_OP.fullmatch(a):
            i += 2; continue
        if _REDIR_ATTACHED.fullmatch(a):
            i += 1; continue
        if re.fullmatch(r"-[a-zA-Z]*s[a-zA-Z]*", a) and not has_c:
            stdin_s = True
        if a == "-":
            stdin_s = True
        elif not a.startswith(("-", "+")):
            files.append(a)
        i += 1
    if has_c:
        return check_bash(script, depth + 1, *ctx) if script else None
    if stdin_s or not files or files[0].startswith("/dev/"):
        return "標準入力から読ませるシェル(パイプ・リダイレクト越しのスクリプトは中身を確認できない)"
    return None


def _env_split_string(toks):
    """env -S / --split-string の引数を、続きのコマンドと合わせて1つの文字列に戻す(なければ None)。"""
    for k, t in enumerate(toks[1:], 1):
        if t in ("-S", "--split-string") and k + 1 < len(toks):
            return " ".join(toks[k + 1:])
        if t.startswith("--split-string="):
            return " ".join([t.split("=", 1)[1]] + toks[k + 1:])
        if t.startswith("-S") and len(t) > 2:
            return " ".join([t[2:]] + toks[k + 1:])
    return None


def _check_tokens(toks, depth, ctx):
    n = 0
    while n < len(toks) and re.fullmatch(r"\w+=.*", toks[n]):
        n += 1
    toks = toks[n:]
    if not toks:
        return None
    if depth > _MAX_DEPTH:
        return "コマンドの入れ子が深すぎて中身を確認できない"
    reason = _check_cd(toks, *ctx)
    if reason:
        return reason
    prog = _base(toks[0]).casefold()
    if prog == "env":
        inner = _env_split_string(toks)
        if inner is not None:
            return check_bash(inner, depth + 1, *ctx)
    if prog in _WRAPPERS:
        for k in range(1, len(toks)):
            if _base(toks[k]).casefold() in _GIT_LIKE:
                return _check_tokens(toks[k:], depth + 1, ctx)
        return None
    if prog == "git-send-email":
        return "git send-email"
    if prog == "git":
        return check_git(toks[1:])
    if prog == "gh":
        return check_gh(toks[1:])
    if prog == "eval":
        return check_bash(" ".join(toks[1:]), depth + 1, *ctx)
    if prog in _SHELLS:
        return _shell_script_reason(toks, depth, ctx)
    return None


def _check_indirection(all_words, norm):
    """xargs / parallel / find -exec は、コマンドに git か gh のコマンド語が現れたら止める(何を渡すか追えないため)。"""
    if not any(_is_git_word(w) for w in _WORD_SPLIT.split(norm) if w):
        return None
    for k, w in enumerate(all_words):
        base = _base(w).casefold()
        if base in ("xargs", "parallel"):
            return f"{base} 経由の git / gh 呼び出し"
        if base == "find" and any(x in _FIND_EXEC for x in (y.casefold() for y in all_words[k + 1:])):
            return "find -exec 経由の git / gh 呼び出し"
    return None


def check_bash(cmd, depth=0, cwd=None, home=None):
    """止めるべきなら理由(日本語の短い説明)を、通してよければ None を返す。cwd は呼び出し時の作業ディレクトリ。"""
    if depth > _MAX_DEPTH + 1:
        return "コマンドの入れ子が深すぎて中身を確認できない"
    home = home or os.path.expanduser("~")
    ctx = (cwd, home)
    segments = split_segments(cmd)
    norm = cmd.replace('"', "").replace("'", "").replace("\\", "")
    for reason in (check_tamper(cmd, segments, cwd, home), _check_env(norm), _check_catch_all(norm)):
        if reason:
            return reason
    token_lists = [_tokens(seg) for seg in segments]
    reason = _check_indirection([w for toks in token_lists for w in toks], norm)
    if reason:
        return reason
    for toks in token_lists:
        reason = _check_tokens(toks, depth, ctx)
        if reason:
            return reason
    return None
