"""night-mode-guard: git / gh サブコマンドの判定(純関数のみ・I/O なし)。

git は許可リスト方式(ローカル・読み取りだけ通す)、gh は読み取りだけ通す。検出網であり境界ではない(ADR-028)。
"""
import re

_VALUE_OPTS = {"-C", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
# 夜間モード中に通す git のサブコマンド。これ以外(push・send-email・別名・未知)は止める。
ALLOWED = {"add", "commit", "status", "log", "diff", "show", "branch", "checkout", "switch", "restore",
           "reset", "rev-parse", "worktree", "merge", "rebase", "cherry-pick", "tag", "fetch", "pull",
           "ls-files", "grep", "blame", "init", "clone", "describe", "shortlog", "reflog", "stash",
           "config", "rm", "mv", "revert", "apply", "am", "format-patch", "clean", "rev-list",
           "merge-base", "ls-remote", "cat-file", "diff-tree", "show-ref", "for-each-ref", "name-rev",
           "symbolic-ref", "bisect", "remote"}
_CONFIG_READ = {"--get", "--get-all", "--list", "-l"}
# 長いオプションは、他と紛れない前置きだけでも通じる(--upl = --upload-pack)。危険な名前の前置きは同じ扱いにする。
_DANGEROUS_LONG = ("template", "upload-pack", "receive-pack")
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


def _long_prefix(arg, names):
    """`--X[=v]` が names のどれかの前置き(2字以上)なら True。"""
    if not arg.startswith("--") or arg == "--":
        return False
    name = arg[2:].split("=", 1)[0]
    return len(name) >= 2 and any(n.startswith(name) for n in names)


def _short_flags(arg):
    """`-abc` / `-ca=b` の文字(単独ダッシュで、英字だけの束のとき)。"""
    if arg.startswith("--") or not arg.startswith("-"):
        return ""
    flags = arg[1:].split("=", 1)[0]
    return flags if re.fullmatch(r"[A-Za-z]+", flags) else ""


def _git_sub(args):
    """グローバルオプションを飛ばして (サブコマンド, 残りの引数, 設定上書きの有無) を返す。"""
    i, config = 0, False
    while i < len(args):
        a = args[i]
        if a in ("-c", "--config-env") or _long_prefix(a, ("config-env",)):
            config = True
            i += 1 if "=" in a else 2
            continue
        if re.match(r"-c.", a) and not a.startswith("--"):
            config = True; i += 1; continue
        if a in _VALUE_OPTS:
            i += 2; continue
        if a.startswith("-"):
            i += 1; continue
        return a, args[i + 1:], config
    return None, [], config


def _check_sub_args(sub, rest):
    for a in rest:
        if a == "--":
            break
        flags = _short_flags(a)
        if (_long_prefix(a, _DANGEROUS_LONG) or "ext::" in a
                or (sub == "rebase" and (_long_prefix(a, ("exec",)) or "x" in flags))
                or (sub == "clone" and (_long_prefix(a, ("config",)) or "c" in flags))
                or (sub in ("fetch", "pull", "clone") and "u" in flags)):
            return f"git {sub} の設定上書き・外部コマンドを走らせる指定({a})"
    return None


def check_git(args):
    sub, rest, config = _git_sub(args)
    if config:
        return "git -c(設定の上書き。別名や外部コマンドの経路になるため)"
    if sub is None:
        return None
    if sub not in ALLOWED:
        return f"git {sub}(夜間モードで通すのはローカルの git だけ)"
    if sub == "config" and not (_CONFIG_READ & set(rest)):
        return "git config の書き込み"
    if sub == "remote" and not (rest == [] or rest == ["-v"] or rest[0] in ("show", "get-url")):
        return "git remote の変更"
    if sub == "bisect" and rest[:1] == ["run"]:
        return "git bisect run(任意のコマンドを走らせるため)"
    if sub == "symbolic-ref" and (len([a for a in rest if not a.startswith("-")]) != 1
                                  or {"-d", "--delete", "-m"} & set(rest)):
        return "git symbolic-ref の書き込み"
    return _check_sub_args(sub, rest)


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


def check_gh(args):
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
    if not subs or subs[0] == "search":
        return None
    if subs[0] == "api":
        return _check_gh_api(args[i + 1:])
    if len(subs) == 2 and subs[1] in _GH_READ.get(subs[0], ()):
        return None
    return "gh " + " ".join(subs) + "(読み取り以外の gh)"
