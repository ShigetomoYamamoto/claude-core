"""night-mode-guard の Bash 判定(純関数のみ・I/O なし)。

コマンド文字列を、クォートを考慮して区切り、各コマンドの先頭語を見る。
`g"it" push` / `\\git push` / `git -C x push` / `sh -c '...'` / `sudo git push` も同じ形に直して判定する。
これは検出網であり境界ではない(ADR-028)。curl での POST などは見ない。
"""
import re
import shlex

_GIT_LIKE = {"git", "gh", "git-send-email", "sh", "bash", "zsh", "dash", "ksh", "eval"}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
_WRAPPERS = {"command", "builtin", "sudo", "env", "time", "nohup", "exec", "nice", "xargs",
             "then", "do", "else", "if", "while", "until", "!", "timeout", "stdbuf"}
_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
_GIT_BLOCKED = {"push", "send-email"}
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
_PROTECTED = (".claude/settings.json", ".claude/settings.local.json", ".claude/hooks/", "night-mode")
_WORKOPS_NIGHT = re.compile(r"\bworkops\b.*\bnight\b.*\b(?:start|end)\b")
_INLINE_PUSH = re.compile(r"\bgit\b.*\bpush\b|\bsend-email\b|\bgh\b\W+(?:pr|issue|release|api|repo|workflow|gist)\b")


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


def _check_git(args):
    i = 0
    while i < len(args):
        a = args[i]
        if a in _GIT_VALUE_OPTS:
            i += 2; continue
        if a.startswith("-"):
            i += 1; continue
        return f"git {a}" if a in _GIT_BLOCKED else None
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


def _check_tokens(toks, depth):
    n = 0
    while n < len(toks) and re.fullmatch(r"\w+=.*", toks[n]):
        n += 1
    toks = toks[n:]
    if not toks or depth > 3:
        return None
    prog = _base(toks[0])
    if prog in _WRAPPERS:
        for k in range(1, len(toks)):
            if _base(toks[k]) in _GIT_LIKE:
                return _check_tokens(toks[k:], depth + 1)
        return None
    if prog in ("git-send-email",):
        return "git send-email"
    if prog == "git":
        return _check_git(toks[1:])
    if prog == "gh":
        return _check_gh(toks[1:])
    if prog == "eval":
        return check_bash(" ".join(toks[1:]), depth + 1)
    if prog in _SHELLS:
        for k, t in enumerate(toks[1:-1], 1):
            if re.fullmatch(r"-[a-z]*c", t):
                return check_bash(toks[k + 1], depth + 1)
    return None


def check_bash(cmd, depth=0):
    """止めるべきなら理由(日本語の短い説明)を、通してよければ None を返す。"""
    norm = cmd.replace('"', "").replace("'", "").replace("\\", "")
    for text in (cmd, norm):
        for key in _PROTECTED:
            if key in text:
                return f"夜間モードの設定や安全装置に触れるコマンド({key})"
    if _WORKOPS_NIGHT.search(norm):
        return "夜間モードの開始・終了コマンド(workops night)"
    for seg in split_segments(cmd):
        reason = _check_tokens(_tokens(seg), depth)
        if reason:
            return reason
    if re.search(r"\b(?:python[\d.]*|node|perl|ruby|php)\b[^\n]*(?:\s-[cer]\b|<<)", cmd) and _INLINE_PUSH.search(norm):
        return "インタプリタ経由の push / gh 呼び出しの疑い"
    return None
