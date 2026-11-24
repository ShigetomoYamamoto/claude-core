"""night-mode-guard: Bash 経由のマーカー・設定・hook の改ざんを検出する(純関数のみ・I/O なし)。

文字列の検出網であり境界ではない(ADR-028 / ADR-036 の限界)。変数展開や、文字列を組み立てて
実行する手口、スクリプトファイルの中身は見ない。
"""
import fnmatch
import os
import posixpath
import re
import shlex

MARKER_NAME = "night-mode.json"
_NIGHT = re.compile(r"night[-_]?mode", re.I)
_PROTECTED = (".claude/settings", ".claude/hooks")
_WORKOPS_NIGHT = re.compile(r"\bworkops\b.*\bnight\b.*\b(?:start|end)\b", re.I)
_MUTATORS = {"rm", "rmdir", "mv", "cp", "ln", "find", "tee", "truncate", "chmod", "chown", "chflags",
             "install", "rsync", "unlink", "shred", "dd", "ditto"}
_INPLACE_PROGS = {"sed", "perl"}
_INPLACE_FLAG = re.compile(r"-[a-zA-Z]*i|--in-place")
_NOISE_REDIRECT = re.compile(r"\d*>>?\s*/dev/null|&>\s*/dev/null|\d*>&\d+-?")
_GLOB_CHARS = re.compile(r"[*?\[]")
# .git/config・.git/hooks/*・.git/info/*(worktree 側の gitdir も)。ここに書くと git が任意コマンドを走らせうる。
_GIT_INTERNAL = re.compile(r"\.git/(?:(?:worktrees|modules)/[^/\s]+/)*(?:config|hooks|info)(?![\w-])")


def _squeeze(cmd):
    """クォート・バックスラッシュ・波括弧を取り除く(組み立てられた語を素の形に戻す)。"""
    return re.sub(r"[\"'\\{}]", "", cmd)


def _outside_quotes(cmd):
    """クォートの中身を落とした文字列(リダイレクト記号の検出用)。"""
    out, quote, i = [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and quote != "'":
            i += 2; continue
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _has_redirect(cmd):
    return ">" in _NOISE_REDIRECT.sub("", _outside_quotes(cmd))


def _words(segments):
    words = []
    for seg in segments:
        try:
            words.extend(shlex.split(seg, posix=True))
        except ValueError:
            words.extend(re.sub(r"[\"'()`]", " ", seg).replace("\\", "").split())
    return words


def _has_mutator(words):
    for k, w in enumerate(words):
        base = w.rsplit("/", 1)[-1].casefold()
        if base in _MUTATORS:
            return True
        if base in _INPLACE_PROGS and any(_INPLACE_FLAG.match(x) for x in words[k + 1:k + 8]):
            return True
    return False


def _glob_comps(text):
    comps = []
    for w in re.split(r"\s+", text):
        comps.extend(c for c in w.split("/") if c and _GLOB_CHARS.search(c))
    return comps


def _glob_hits_claude_or_marker(squeezed):
    """.claude ディレクトリかマーカーに当たりうる glob があるか(`*` だけの語は除く)。"""
    hits_dir = hits_marker = False
    for comp in _glob_comps(squeezed):
        if set(comp) <= set("*"):
            continue
        if comp.startswith(".") and fnmatch.fnmatch(".claude", comp):
            hits_dir = True
        if not comp.startswith(".") and fnmatch.fnmatch(MARKER_NAME, comp):
            hits_marker = True
    return hits_dir, hits_marker


def _neutralize_worktrees(text, home):
    """`.claude/worktrees/` はプロジェクトの作業ツリー置き場なので、.claude の言及に数えない。

    ただしホームの .claude(`~/`・`$HOME/`・`${HOME}/`・ホームの絶対パス)の下は数える。
    """
    pat = re.compile(r"((?:~|\$\{?home\}?|%s)/)?\.claude/worktrees/" % re.escape(home.casefold()))
    return pat.sub(lambda m: m.group(0) if m.group(1) else ".wt/", text)


def cwd_in_claude(cwd, home):
    """作業ディレクトリが、ホームの .claude の中、または .claude/worktrees/* 以外の .claude の中か。"""
    if not cwd:
        return False
    c = posixpath.normpath(str(cwd)).casefold()
    hc = posixpath.normpath(posixpath.join(home, ".claude")).casefold()
    if c == hc or c.startswith(hc + "/"):
        return True
    comps = c.split("/")
    return any(comp == ".claude" and (i + 1 >= len(comps) or comps[i + 1] != "worktrees")
               for i, comp in enumerate(comps))


def check_tamper(cmd, segments, cwd=None, home=None):
    """止めるべきなら理由を、通してよければ None を返す。segments は区切り済みのコマンド列。"""
    home = home or os.path.expanduser("~")
    cmd = _neutralize_worktrees(cmd.casefold(), home)  # macOS の既定のファイルシステムは大文字小文字を区別しない
    squeezed = _neutralize_worktrees(_squeeze(cmd), home)
    for text in (cmd, squeezed):
        if _NIGHT.search(text):
            return "夜間モードのマーカーや開始・終了コマンドに触れる語(night-mode)"
        if _WORKOPS_NIGHT.search(text):
            return "夜間モードの開始・終了コマンド(workops night)"
        for key in _PROTECTED:
            if key in text:
                return f"夜間モードの設定や安全装置に触れるコマンド({key})"
    hits_dir, hits_marker = _glob_hits_claude_or_marker(squeezed)
    mentions = (".claude" in cmd or ".claude" in squeezed or hits_dir or bool(_GIT_INTERNAL.search(squeezed))
                or cwd_in_claude(cwd, home))
    if not mentions:
        return None
    if hits_marker:
        return "マーカーに当たりうるワイルドカードと .claude を含むコマンド"
    if _has_mutator(_words(segments)):
        return ".claude を変更しうるコマンド(rm・mv・cp・find・sed -i など)"
    if _has_redirect(cmd):
        return ".claude を含むコマンドでのリダイレクト書き込み"
    return None
