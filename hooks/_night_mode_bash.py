"""night-mode-guard の Bash 判定(純関数のみ・I/O なし)。

コマンド文字列を、クォートを考慮して区切り、各コマンドの先頭語を見る。
`g"it" push` / `\\git push` / `git -C x push` / `sh -c '...'` / `sudo git push` も同じ形に直して判定する。
これは検出網であり境界ではない(ADR-028)。curl での POST・スクリプトファイルの中身・
インタプリタ内の subprocess などは見ない(ADR-036 の限界)。
"""
import re
import shlex

from _night_mode_tamper import check_tamper

_GIT_LIKE = {"git", "gh", "git-send-email", "sh", "bash", "zsh", "dash", "ksh", "eval"}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
_WRAPPERS = {"command", "builtin", "sudo", "env", "time", "nohup", "exec", "nice", "xargs",
             "then", "do", "else", "if", "while", "until", "!", "timeout", "stdbuf"}
_GIT_VALUE_OPTS = {"-C", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_GIT_CONFIG_OPTS = {"-c", "--config-env"}
# 夜間モード中に通す git のサブコマンド(ローカル・読み取り中心)。これ以外(push・send-email・別名・未知)は止める。
_GIT_ALLOWED = {"add", "commit", "status", "log", "diff", "show", "branch", "checkout", "switch", "restore",
                "reset", "rev-parse", "worktree", "merge", "rebase", "cherry-pick", "tag", "fetch", "pull",
                "ls-files", "grep", "blame", "init", "clone", "describe", "shortlog", "reflog", "stash",
                "config"}
_GIT_CONFIG_READ = {"--get", "--get-all", "--list", "-l"}
_GIT_ENV = re.compile(r"(?<![\w])(?:GIT_\w*|EDITOR|VISUAL|SSH_ASKPASS)=")
_GIT_TOKEN = re.compile(r"(?<![\w])(?:git|gh)(?![\w])")
_MAX_DEPTH = 3
_GH_READ = {
    "pr": {"view", "list", "status", "diff", "checks"},
    "issue": {"view", "list", "status"},
    "run": {"view", "list", "watch"},
    "workflow": {"view", "list"},
    "release": {"view", "list", "download"},
    "repo": {"view", "clone"},
    "auth": {"status"},
}
_GH_WRITE_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}
_INLINE_PUSH = re.compile(r"\bgit\b.*\bpush\b|\bsend-email\b|\bgh\b\W+(?:pr|issue|release|api|repo|workflow|gist)\b")
_FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
_REDIR_OP = re.compile(r"\d*(?:<<<|<<-?|<>|<|>>|>\|?|&>)")
_REDIR_ATTACHED = re.compile(r"\d*(?:<<<|<<-?|<|>>|>)\S+")


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


def _base(tok):
    return tok.rsplit("/", 1)[-1]


def _git_sub(args):
    """グローバルオプションを飛ばして (サブコマンド, 残りの引数, -c の有無) を返す。"""
    i, config = 0, False
    while i < len(args):
        a = args[i]
        if a in _GIT_CONFIG_OPTS or a.startswith("--config-env="):
            config = True
        if a in _GIT_VALUE_OPTS or a in _GIT_CONFIG_OPTS:
            i += 2; continue
        if a.startswith("-"):
            i += 1; continue
        return a, args[i + 1:], config
    return None, [], config


def _check_git(args, depth):
    sub, rest, config = _git_sub(args)
    if config:
        return "git -c(設定の上書き。別名や外部コマンドの経路になるため)"
    if sub is None:
        return None
    if sub not in _GIT_ALLOWED:
        return f"git {sub}(夜間モードで通すのはローカルの git だけ)"
    if sub == "config" and not (_GIT_CONFIG_READ & set(rest)):
        return "git config の書き込み"
    if sub == "rebase" and any(a.startswith(("-x", "--ex")) for a in rest):
        return "git rebase --exec(任意のコマンドを走らせるため。中身は確認しない)"
    for a in rest:
        if (a == "-c" or re.match(r"-c.+=", a) or a.startswith(("--conf", "--template", "--upl", "--rec"))
                or "ext::" in a or (a == "-u" and sub in ("fetch", "pull", "clone"))):
            return f"git {sub} の設定上書き・外部コマンドを走らせる指定({a})"
    return None


def _check_gh_api(args):
    for k, a in enumerate(args):
        if a in _GH_WRITE_FLAGS or a.startswith(("--field=", "--raw-field=", "--input=")):
            return "gh api(書き込みの引数つき)"
        if re.fullmatch(r"-[fF].+", a):
            return "gh api(書き込みの引数つき)"
        m = re.fullmatch(r"(?:-X=?|--method=?)(.*)", a)
        if m:
            method = m.group(1) or (args[k + 1] if k + 1 < len(args) else "")
            if method.upper() != "GET":
                return f"gh api(メソッド {method})"
    return None


def _check_gh(args):
    subs, i = [], 0
    while i < len(args) and len(subs) < 2:
        a = args[i]
        if a in ("-R", "--repo"):
            i += 2; continue
        if not a.startswith("-"):
            subs.append(a)
            if subs[0] in ("api", "search"):
                break
        i += 1
    if not subs:
        return None
    if subs[0] == "search":
        return None
    if subs[0] == "api":
        return _check_gh_api(args[i + 1:])
    if len(subs) == 2 and subs[1] in _GH_READ.get(subs[0], ()):
        return None
    return "gh " + " ".join(subs) + "(読み取り以外の gh)"


def _shell_script_reason(toks, depth):
    """シェル呼び出しの判定。-c の中身は再帰、標準入力から読む形は止める、スクリプトファイルは通す。"""
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
        return check_bash(script, depth + 1) if script else None
    if stdin_s or not files or files[0].startswith("/dev/"):
        return "標準入力から読ませるシェル(パイプ・リダイレクト越しのスクリプトは中身を確認できない)"
    return None


def _check_tokens(toks, depth):
    n = 0
    while n < len(toks) and re.fullmatch(r"\w+=.*", toks[n]):
        n += 1
    toks = toks[n:]
    if not toks:
        return None
    if depth > _MAX_DEPTH:
        return "コマンドの入れ子が深すぎて中身を確認できない"
    prog = _base(toks[0]).casefold()
    if prog in _WRAPPERS:
        for k in range(1, len(toks)):
            if _base(toks[k]).casefold() in _GIT_LIKE:
                return _check_tokens(toks[k:], depth + 1)
        return None
    if prog in ("git-send-email",):
        return "git send-email"
    if prog == "git":
        return _check_git(toks[1:], depth)
    if prog == "gh":
        return _check_gh(toks[1:])
    if prog == "eval":
        return check_bash(" ".join(toks[1:]), depth + 1)
    if prog in _SHELLS:
        return _shell_script_reason(toks, depth)
    return None


def _check_indirection(all_words, norm):
    """xargs / parallel / find -exec は、コマンド内に git か gh が現れたら止める(何を渡すか追えないため)。"""
    if not _GIT_TOKEN.search(norm):
        return None
    for k, w in enumerate(all_words):
        base = _base(w)
        if base in ("xargs", "parallel"):
            return f"{base} 経由の git / gh 呼び出し"
        if base == "find" and any(x in _FIND_EXEC for x in all_words[k + 1:]):
            return "find -exec 経由の git / gh 呼び出し"
    return None


def check_bash(cmd, depth=0):
    """止めるべきなら理由(日本語の短い説明)を、通してよければ None を返す。"""
    if depth > _MAX_DEPTH + 1:
        return "コマンドの入れ子が深すぎて中身を確認できない"
    segments = split_segments(cmd)
    norm = cmd.replace('"', "").replace("'", "").replace("\\", "")
    reason = check_tamper(cmd, segments)
    if reason:
        return reason
    if _GIT_ENV.search(norm):
        return "git の設定を環境変数で上書きするコマンド(GIT_CONFIG* など)"
    token_lists = [_tokens(seg) for seg in segments]
    reason = _check_indirection([w for toks in token_lists for w in toks], norm)
    if reason:
        return reason
    for toks in token_lists:
        reason = _check_tokens(toks, depth)
        if reason:
            return reason
    if re.search(r"\b(?:python[\d.]*|node|perl|ruby|php)\b[^\n]*(?:\s-[cer]\b|<<)", cmd) and _INLINE_PUSH.search(norm):
        return "インタプリタ経由の push / gh 呼び出しの疑い"
    return None
