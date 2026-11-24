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
    "git config -l", "git -C /x status", "git --no-pager log", "git commit -C abc", "git commit -c abc", "git log -c", "git diff -c", "git rm a", "git mv a b", "git revert HEAD",
    "git apply x.patch", "git am x.mbox", "git format-patch -1", "git clean -n", "git rev-list HEAD", "git merge-base a b",
    "git ls-remote origin", "git cat-file -p HEAD", "git diff-tree HEAD", "git show-ref", "git for-each-ref", "git name-rev HEAD",
    "git symbolic-ref HEAD", "git symbolic-ref --short HEAD", "git bisect start", "git bisect good", "git remote", "git remote -v",
    "git remote show origin", "git remote get-url origin", "GIT_EDITOR=true git rebase --continue", "GIT_SEQUENCE_EDITOR=: git rebase main",
    "EDITOR=true git commit", "VISUAL=: git commit", "GIT_PAGER=cat git log", "PAGER=cat git log", "GIT_TERMINAL_PROMPT=0 git fetch",
    "GIT_EDITOR='true' git commit", "git diff --config=a=b",
    "git log --color", "git log --color=always", "git diff --exit-code", "git ls-files --exclude=x", "git pull --recurse-submodules",
    "git rebase --empty=drop main", "git fetch --tags", "git rebase -i main", "git clone --depth 1 u", "git clone --recurse-submodules u", "git rebase --continue", "git rebase main",
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
    "EDITOR=x git commit", "GIT_EDITOR=vim git commit", "GIT_EDITOR=true GIT_DIR=x git status", "PAGER=less git log",
    "GIT_TERMINAL_PROMPT=1 git fetch", "git notes add -m x", "git remote add o u", "git remote set-url o u", "git remote rm o",
    "git symbolic-ref HEAD refs/heads/x", "git bisect run sh t.sh", "git clone -c core.fsmonitor=x u", "git clone --config=x u",
    "git clone -ca=b u",
    "git clone --conf=x u", "git clone --config x u", "git fetch --upl x o", "git pull --rec=x o", "git clone --templ=x u",
    "git rebase --ex true main", "git rebase -ix true", "git clone -qc a=b u", "git fetch -pu", "git --config-e=a=B status",
    "git clone --upload-pa=x u", "echo o | XARGS GIT push", "echo o | xargs /usr/bin/GIT push", "FIND . -EXEC git status {} +",
    "python3 -c \"import subprocess; subprocess.run(['GIT','PUSH'])\"", "git -ca=b status", "git -c a=b commit -c abc", "VISUAL=x git commit",
    "SSH_ASKPASS=x git fetch", "env GIT_PAGER=x git log", "env EDITOR=x git commit", "FOO=1 GIT_DIR=x git status",
    "git clone --template=/x u", "git clone -u x u",
    "git fetch -u", "git pull --upload-pack=x",
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

CATCH_ALL_BLOCKED = [
    "python3 -c \"import subprocess; subprocess.run(['git','push'])\"",
    "node -e \"require('child_process').execSync('git push')\"", "osascript -e 'do shell script \"git push\"'",
    "unknownwrap git push", "grep 'git push' x", "git commit -m 'fix push bug'", "echo git send-email",
    "python3 -c \"import os; os.system('gh pr create')\"", "x gh pr merge 3", "x gh issue comment 3", "x gh release upload v1 f",
    "x gh repo fork", "x gh workflow run a.yml", "x gh api -X POST y", "x gh api y --method=PATCH", "x gh api y -f a=b",
    "x gh api y --input f", "x GH PR REVIEW 3", "python3 - <<EOF\nimport subprocess\nsubprocess.run(['git', 'push'])\nEOF",
    "env -S 'git push'", "env -S'git push'", "env --split-string='git push'", "env -S 'sh -c \"git push\"'",
    "caffeinate git push", "doas git push", "script -q /dev/null git push", "arch -arm64 git push", "watch git push",
    "flock l git push", "fish -c 'git push'", "csh -c 'git push'", "tcsh -c 'git push'", "ksh -c 'git push'",
    "fish", "caffeinate sh", "echo x | tcsh", "caffeinate git frobnicate",
]

GH_DENY_UNLESS_READ = [
    "python3 -c \"print('gh', 'gist', 'create')\"", "x gh gist create f", "x gh secret set A", "x gh variable set A",
    "x gh label create l", "x gh run rerun 5", "x gh run cancel 5", "x gh run delete 5", "x gh repo sync", "x gh repo rename n",
    "x gh repo archive", "x gh pr", "x gh codespace create", "x gh extension install x", "x gh alias set a b",
    "x gh ssh-key add k", "x gh cache delete 1", "echo gh is great", "x GH GIST CREATE",
    "subprocess.run(['gh','pr','create'])", "x gh -R o/r pr create",
]

GH_SECOND_NET_BLOCKED = [
    "x gh pr view 3; echo pr create", "x gh pr view 3 && echo issue comment 3", "x gh api repos/o/r; curl -X POST u",
    "x gh run list | echo release upload", "x gh auth status; echo repo fork", "gh pr view 3 ; workflow run",
    "gh pr list --json number; echo '-f a=b' api",
]

GH_READ_ALLOWED = [
    "x gh pr view 3", "x gh pr list", "x gh issue view 3", "x gh run watch 5", "x gh -R o/r pr view 3", "x gh api repos/o/r",
    "x gh api -X GET repos/o/r", "x gh search issues foo", "x gh release download v1", "x gh repo view", "x gh auth status",
    "x gh workflow list", "x gh pr checks 3", "x gh --version", "git log --grep gh",
]

CATCH_ALL_ALLOWED = ["env -S 'ls -l'", "caffeinate pnpm test", "watch ls", "arch -arm64 pnpm test", "flock l pnpm test",
                     "fish scripts/t.fish", "gh api repos/o/r/pulls", "gh pr view 3", "env A=1 ls"]

INDIRECTION_ALLOWED = [
    "bash scripts/test.sh", "sh ./build.sh arg", "bash -c 'ls'", "bash -c -- 'ls'", "bash -n x.sh",
    "bash --version", "find . -name '*.py' -exec wc -l {} +", "ls | xargs wc -l", "echo a | parallel echo",
    "find . -type f", "bash -x scripts/test.sh", "pnpm test", "bash -o pipefail scripts/t.sh",
    "bash -O extglob scripts/t.sh", "bash +o history scripts/t.sh", "bash --rcfile r.sh scripts/t.sh",
    "bash -o pipefail -c 'ls'",
    "find . -path ./.git -prune -o -name '*.ts' -exec wc -l {} +", "ls .git | xargs wc -l", "find .github -exec wc -l {} +",
    "find . -path ./.git/x -exec ls {} +",
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
    "echo x > ~/.CLAUDE/settings.json", "rm ~/.Claude/x", "RM ~/.claude/x", "cd ~/.claude && rm n*", "echo {} > .claude/settings.local.json", "rm $HOME/.claude/x",
    "rm ${HOME}/.claude/worktrees/x", "rm ~/.claude/worktrees/x", "rm -rf .claude/worktrees", "rm .claude",
    "rm .claude/worktrees/w/.claude/hooks/x", "rm .claude/worktrees/w/.claude/settings.json", "rm .claude/rules/x.md",
    "rm .claude/worktrees/../settings.json", "echo x > ~/.claude/worktrees/../night-mode.json",
    "rm .claude/worktrees/x/../../settings.json", "echo x > .claude/worktrees/..", "rm .claude/worktrees/x/..",
    "echo x > .claude/worktrees/x/../x/../../hooks/a", "rm .claude/worktrees/\"..\"/x", "rm .claude/worktrees/../x",
    "cp a .claude/worktrees/w/../../rules/b",
    "rm .claude/worktrees/w/night-mode.json", "cd .claude && rm x", "rm /r/.claude/", "cat ~/.CLAUDE/NIGHT-MODE.JSON",
    "ls ~/.CLAUDE/HOOKS/", "rm ~/.CLAUDE/NIGHT*",
    "echo x > repo/.git/config", "rm repo/.git/hooks/pre-push", "cp x .git/hooks/pre-commit", "tee .git/info/exclude",
    "sed -i s/a/b/ .git/config", "rm .GIT/HOOKS/x", "echo x >> .git/worktrees/w/config", "chmod +x .git/hooks/pre-push",
    "rm .git/modules/m/hooks/x", "echo x > .git/modules/a/modules/b/config", "cp x .git/worktrees/w/modules/m/info/y",
]

TAMPER_ALLOWED = [
    "ls ~/.claude", "cat ~/.claude/rules/x.md", "git add .claude/rules/x.md", "git status 2>/dev/null",
    "ls .claude/agents 2>&1", "git commit -m 'fix .claude rules install'", "cat .claude/CLAUDE.md > /dev/null",
    "echo x > out.txt", "rm out.txt", "ls ~/.claude/*.md", "grep -r foo .claude/rules", "pnpm install",
    "sed -n 1,5p .claude/rules/x.md", "cat .git/config", "ls .git/hooks", "git status > out.txt",
    "rm out/.gitignore", "rm .claude/worktrees/x/a.txt", "echo x > /repo/.claude/worktrees/w/out.txt",
    "cp a /repo/.claude/worktrees/w/b", "rm -rf .CLAUDE/Worktrees/x/a", "mv .claude/worktrees/w/a .claude/worktrees/w/b",
    "sed -i s/a/b/ /r/.claude/worktrees/w/f.md", "cat .git/info/exclude", "git commit -m 'fix hooks' -- a.py", "ls *.json",
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

    def test_catch_all_blocked(self):
        self.check(CATCH_ALL_BLOCKED, True)

    def test_gh_deny_unless_read(self):
        self.check(GH_DENY_UNLESS_READ, True)
        self.check(GH_READ_ALLOWED, False)

    def test_gh_second_net_still_blocks(self):
        self.check(GH_SECOND_NET_BLOCKED, True)

    def test_git_config_single_operand_is_read(self):
        self.check(["git config user.name", "git config --global user.name", "git config --local core.editor",
                    "git config --show-origin user.email", "git config list", "git config --global list",
                    "git config get user.name", "git config get --global user.name", "git config remote.origin.url"], False)
        self.check(["git config user.name x", "git config --unset user.name", "git config --unset-all x",
                    "git config --add a b", "git config --edit", "git config -e", "git config --replace-all a b",
                    "git config --global --remove-section x", "git config --uns user.name", "git config",
                    "git config edit", "git config set a.b c", "git config unset a.b", "git config rename-section a b",
                    "git config remove-section a", "git config get", "git config get a.b c", "git config list x",
                    "git config get-color x", "git config get-colorbool x", "git config username", "git config get username",
                    "git config get list", "git config list list", "git config --global edit"], True)

    def test_catch_all_allowed(self):
        self.check(CATCH_ALL_ALLOWED, False)

    def test_cwd_inside_claude_applies_tamper_checks(self):
        home = "/h"
        for cwd in ["/h/.claude", "/h/.claude/rules", "/r/.claude", "/r/.claude/rules", "/h/.claude/worktrees/w",
                    "/R/.CLAUDE/x"]:
            for cmd in ["rm a", "echo x > f", "mv a b", "sed -i s/a/b/ f", "tee f", "cp a b"]:
                self.assertTrue(check_bash(cmd, 0, cwd, home), f"{cwd}: {cmd}")
            for cmd in ["ls", "cat a", "pnpm test", "git status"]:
                self.assertIsNone(check_bash(cmd, 0, cwd, home), f"{cwd}: {cmd}")

    def test_cwd_outside_claude_or_in_project_worktree_allowed(self):
        home = "/h"
        for cwd in ["/r", "/h", "/r/.claude/worktrees/w", "/r/.claude/worktrees/w/src", "/r/.claude/worktrees", None]:
            for cmd in ["rm a", "echo x > f", "cp a b"]:
                self.assertIsNone(check_bash(cmd, 0, cwd, home), f"{cwd}: {cmd}")

    def test_cd_into_home_claude_blocked(self):
        home = "/h"
        for cmd in ["cd /h/.claude", "cd ~/.claude", "pushd $HOME/.claude", "cd ${HOME}/.claude/x", "cd -P ~/.claude",
                    "cd /H/.CLAUDE", "ls && cd ~/.claude", "cd /h/.claude/worktrees/w"]:
            self.assertTrue(check_bash(cmd, 0, "/r", home), cmd)
        self.assertTrue(check_bash("cd .claude", 0, "/h", home))
        for cmd in ["cd /r", "cd ~", "cd /h", "cd /r/.claude/worktrees/w", "cd", "pushd /r"]:
            self.assertIsNone(check_bash(cmd, 0, "/r", home), cmd)

    def test_depth_limit_blocks_with_reason(self):
        deep = "echo hi"
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
                    "gh -R o/r pr view 3"]:
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
                  "/r/.git/worktrees/w/config", "/r/.git/modules/m/config", "/r/.git/modules/a/modules/b/hooks/x",
                  "/r/.git/worktrees/w/modules/m/info/x", "/r/.git/worktrees/w/hooks/x"]:
            self.assertTrue(self.check(p), p)
        for p in ["/r/.gitignore", "/r/.github/config", "/r/src/config", "/r/.git/HEAD"]:
            self.assertIsNone(self.check(p), p)

    def test_marker_still_blocked(self):
        self.assertTrue(self.check(self.marker))


if __name__ == "__main__":
    unittest.main()
