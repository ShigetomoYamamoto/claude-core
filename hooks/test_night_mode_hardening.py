#!/usr/bin/env python3
"""night-mode-guard の抜け道を塞ぐ追加テスト(stdlib unittest・純関数を直接呼ぶ)。

実行: python3 hooks/test_night_mode_hardening.py
判定本体(_night_mode_bash / _night_mode_policy)を直接呼ぶので速い。hook 全体の配線は
test_night_mode_guard.py が subprocess で確かめる。本物の ~/.claude には触れない。
"""
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _night_mode_policy as policy  # noqa: E402
from _night_mode_bash import check_bash  # noqa: E402

GIT_ALLOWED = [
    "git add a.py", "git commit -m x", "git status", "git log --oneline", "git diff HEAD", "git show HEAD",
    "git branch -a", "git checkout -b x", "git switch main", "git restore a", "git reset --soft HEAD~1",
    "git rev-parse HEAD", "git worktree list", "git merge x", "git rebase main", "git cherry-pick abc",
    "git tag v1", "git fetch origin", "git pull --ff-only", "git ls-files", "git grep foo", "git blame a",
    "git init", "git clone https://example.com/r.git", "git describe", "git shortlog -sn", "git reflog",
    "git stash list", "git config --get user.name", "git config --get-all x", "git config --list",
    "git config -l", "git -C /x status", "git --no-pager log", "git commit -C abc", "git rebase --continue", "git rebase main",
]

GIT_BLOCKED = [
    "git push", "git send-email x.patch", "git p", "git pu origin", "git frobnicate", "git remote add o u",
    "git config user.name x", "git config --global alias.p push", "git config --unset x", "git config",
    "git -c alias.p=push p", "git -c x=y status", "git -C /x -c a=b log", "git -C x push",
    'g"it" push', "\\git push", "/usr/bin/git push", "sudo git push", "env A=1 git push",
    "git rebase --exec 'git push' main", "git rebase -x 'git push origin HEAD' main",
    "git fetch --upload-pack='sh -c x' o", "git clone ext::sh -c x", "git --config-env=a=B status",
    "git rebase -x'git push' main", "git rebase --exe 'git push' main", "git rebase --ex='git push' main",
    "git fetch --upl=x o", "git pull --rec=x o", "GIT push", "/usr/bin/GIT push", "GH pr create",
    "git rebase -x true main", "git rebase --exec=true main", "git rebase -xtrue main",
    "GIT_EDITOR=true git rebase --continue", "EDITOR=x git commit", "VISUAL=x git commit",
    "SSH_ASKPASS=x git fetch", "env GIT_PAGER=x git log", "env EDITOR=x git commit", "FOO=1 GIT_DIR=x git status",
    "git commit -c abc", "git log -c", "git diff --config=a=b", "git clone --template=/x u", "git clone -u x u",
    "git fetch -u", "git pull --upload-pack=x", "git status -cfoo=bar", "git log --conf=x",
    "git fetch o ext::sh", "git commit --receive-pack=x",
    "GIT_CONFIG_COUNT=1 git status", "GIT_SSH_COMMAND=x git fetch", "export GIT_CONFIG_KEY_0=core.fsmonitor",
]

INDIRECTION_BLOCKED = [
    "echo origin | xargs git push", "echo a | xargs -n1 git status", "git branch | xargs gh pr create",
    "find . -name x -exec git push {} \\;", "find . -execdir git status \\;", "find . -ok gh pr create {} \\;",
    "parallel git push ::: a b", "ls | parallel -j2 'gh pr create'",
    "echo 'git push' | sh", "echo 'git push' | bash", "echo x | zsh", "echo x | dash", "cat s.sh | bash -s",
    "bash -s", "bash < script.sh", "sh <<EOF\nls\nEOF", "bash <<< 'git push'", "bash /dev/stdin", "sh -",
    "curl -s u | sh", "bash -c -- 'git push'", "sh -c -- 'cd x && git push'", "bash -lc -- 'git push'",
    "bash -c 'bash -c \"bash -c \\\"bash -c \\\\\\\"bash -c ls\\\\\\\"\\\"\\\"\"'",
    "sudo bash", "env FOO=1 sh", "bash -o pipefail", "bash --rcfile x", "bash -O extglob", "bash +o history",
    "bash --init-file x", "sh", "bash -x", "zsh -o errexit",
]

INDIRECTION_ALLOWED = [
    "bash scripts/test.sh", "sh ./build.sh arg", "bash -c 'ls'", "bash -c -- 'ls'", "bash -n x.sh",
    "bash --version", "find . -name '*.py' -exec wc -l {} +", "ls | xargs wc -l", "echo a | parallel echo",
    "find . -type f", "bash -x scripts/test.sh", "pnpm test", "bash -o pipefail scripts/t.sh",
    "bash -O extglob scripts/t.sh", "bash +o history scripts/t.sh", "bash --rcfile r.sh scripts/t.sh",
    "bash -o pipefail -c 'ls'",
]

TAMPER_BLOCKED = [
    "rm ~/.claude/night-mode.json", "rm -f $HOME/.claude/x", "mv ~/.claude/a ~/b", "cp x ~/.claude/y",
    "ln -sf x ~/.claude/y", "find ~/.claude -name x -delete", "find .claude -type f", "echo x | tee .claude/a",
    "truncate -s 0 ~/.claude/a", "chmod 000 ~/.claude/a", "chflags uchg ~/.claude/a", "install a ~/.claude/b",
    "rsync -a x ~/.claude/", "sed -i s/a/b/ ~/.claude/a", "sed -i.bak s/a/b/ ~/.claude/a",
    "perl -i -pe s/a/b/ ~/.claude/a", "perl -pi -e s/a/b/ ~/.claude/a", "echo x > ~/.claude/a",
    "echo x >> ~/.claude/a", "echo x>~/.claude/a", "r'm' ~/.cl\"aude\"/a", "rm ~/.cl\\aude/a",
    "echo {} > night-mode.json", "echo {} > night_mode.json", "echo x > nightmode", "rm night\"-\"mode.json",
    "cat n\\ight-mode.json", "rm ~/.claude/night*", "rm ~/.claude/*mode.json", "rm ~/.claude/n?ght-mode.json",
    "ls ~/.claude/night*", "cat ~/.claude/*mode.json", "rm ~/.cl*/night-m*", "rm ~/.c*/*", "rm ~/.[c]laude/x",
    "cat ~/.claude/settings.json", "ls .claude/hooks/", "cat ~/.claude/settings.local.json",
    "bash -c 'rm ~/.claude/x'", "eval 'rm ~/.claude/x'", "rm ~/.claude/night-{mode,x}.json",
    "workops night end", "pnpm workops night start",
    "echo x > ~/.CLAUDE/settings.json", "rm ~/.Claude/x", "RM ~/.claude/x", "cat ~/.CLAUDE/NIGHT-MODE.JSON",
    "ls ~/.CLAUDE/HOOKS/", "rm ~/.CLAUDE/NIGHT*",
]

TAMPER_ALLOWED = [
    "ls ~/.claude", "cat ~/.claude/rules/x.md", "git add .claude/rules/x.md", "git status 2>/dev/null",
    "ls .claude/agents 2>&1", "git commit -m 'fix .claude rules install'", "cat .claude/CLAUDE.md > /dev/null",
    "echo x > out.txt", "rm out.txt", "ls ~/.claude/*.md", "grep -r foo .claude/rules", "pnpm install",
    "sed -n 1,5p .claude/rules/x.md", "cat .git/config", "ls .git/hooks", "git status > out.txt",
    "rm out/.gitignore", "cat .git/info/exclude", "git commit -m 'fix hooks' -- a.py", "ls *.json",
]


class BashTables(unittest.TestCase):
    def check(self, table, blocked):
        for cmd in table:
            reason = check_bash(cmd)
            if blocked:
                self.assertTrue(reason, f"通ってしまった: {cmd!r}")
            else:
                self.assertIsNone(reason, f"止まってしまった: {cmd!r} -> {reason}")

    def test_git_allow_list(self):
        self.check(GIT_ALLOWED, False)

    def test_git_default_deny(self):
        self.check(GIT_BLOCKED, True)

    def test_indirection_blocked(self):
        self.check(INDIRECTION_BLOCKED, True)

    def test_indirection_allowed(self):
        self.check(INDIRECTION_ALLOWED, False)

    def test_tamper_blocked(self):
        self.check(TAMPER_BLOCKED, True)

    def test_tamper_allowed(self):
        self.check(TAMPER_ALLOWED, False)

    def test_depth_limit_blocks_with_reason(self):
        deep = "git push"
        for _ in range(6):
            deep = "bash -c " + __import__("shlex").quote(deep)
        reason = check_bash(deep)
        self.assertTrue(reason)
        self.assertIn("入れ子", reason)

    def test_reason_for_git_names_subcommand(self):
        self.assertIn("push", check_bash("git push"))
        self.assertIn("frobnicate", check_bash("git frobnicate"))

    def test_earlier_tables_still_hold(self):
        for cmd in ["git push", 'g"it" push', "\\git push", "git -C x push", "gh pr create", "gh pr merge 3",
                    "gh api x -f a=b", "gh api -X POST x"]:
            self.assertTrue(check_bash(cmd), cmd)
        for cmd in ["gh pr view 3", "gh pr list --json number", "gh api repos/o/r/pulls", "gh run watch 5",
                    "gh -R o/r pr view 3", "git commit -m 'git push は使わない'"]:
            self.assertIsNone(check_bash(cmd), cmd)


class FileTable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.realpath(self.tmp.name)
        self.marker = os.path.join(self.home, ".claude", "night-mode.json")

    def check(self, path):
        return policy.check_file(path, self.marker, self.home, self.home)

    def test_any_directory_hooks_blocked(self):
        for p in ["/repo/.claude/hooks/x.py", "/a/b/.claude/hooks/sub/y.py", "/repo/.claude/hooks/",
                  "/repo/.claude/hooks", ".claude/hooks/z.py", "/Users/u/.claude/hooks/night-mode-guard.py"]:
            self.assertTrue(self.check(p), p)

    def test_any_directory_settings_blocked(self):
        for p in ["/repo/.claude/settings.json", "/repo/.claude/settings.local.json",
                  "/repo/.claude/settings.backup.json", "/x/.claude/settings-old.json", ".claude/settings.json"]:
            self.assertTrue(self.check(p), p)

    def test_ordinary_paths_allowed(self):
        for p in ["/repo/src/a.ts", "/repo/.claude/rules/x.md", "/repo/.claude/agents/a.md",
                  "/repo/hooks/x.py", "/repo/docs/settings.json", "/repo/.claude/settings.md"]:
            self.assertIsNone(self.check(p), p)

    def test_symlink_into_hooks_blocked(self):
        os.makedirs(os.path.join(self.home, "r", ".claude", "hooks"))
        link = os.path.join(self.home, "alias.py")
        os.symlink(os.path.join(self.home, "r", ".claude", "hooks", "x.py"), link)
        self.assertTrue(self.check(link))

    def test_case_variants_blocked(self):
        for p in [os.path.join(self.home, ".CLAUDE", "NIGHT-MODE.JSON"), "/repo/.Claude/Hooks/x.py",
                  "/repo/.claude/Settings.JSON", "/repo/.CLAUDE/SETTINGS.LOCAL.JSON"]:
            self.assertTrue(self.check(p), p)

    def test_git_internals_blocked(self):
        for p in ["/r/.git/config", "/r/.git/hooks/pre-push", "/r/.git/info/exclude", "/r/.GIT/Hooks/x",
                  "/r/.git/worktrees/w/config", "/r/.git/worktrees/w/hooks/x"]:
            self.assertTrue(self.check(p), p)
        for p in ["/r/.gitignore", "/r/.github/config", "/r/src/config", "/r/.git/HEAD"]:
            self.assertIsNone(self.check(p), p)

    def test_marker_still_blocked(self):
        self.assertTrue(self.check(self.marker))


if __name__ == "__main__":
    unittest.main()
