#!/usr/bin/env python3
"""git-destructive-blocker.py の契約テスト（stdlib unittest・依存追加なし）。

実行: python3 -m unittest hooks/test_git_destructive_blocker.py

hook は PreToolUse(Bash) で stdin から JSON を受け取り、保護ブランチ上での
破壊的な git 操作を exit 2 でブロックする。current_branch() は「git が実際に
走るディレクトリ」（`git -C <dir>` / 直前の `cd <dir>`）をコマンド文字列から
推定してそこで評価する（cwd 誤判定バグの修正・本ファイルの主眼）。
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "git-destructive-blocker.py")


def run_hook(command: str, cwd: str) -> int:
    """command を tool_input.command に載せて hook を cwd で起動し exit code を返す。"""
    payload = json.dumps({"tool_input": {"command": command}})
    proc = subprocess.run(
        ["python3", HOOK],
        input=payload,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return proc.returncode


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def init_repo(path: str, branch: str = "main") -> None:
    """path に git init し、branch をカレントブランチにした初期コミット付きリポを作る。"""
    _run(["git", "init", "-b", branch], path)
    _run(["git", "config", "user.email", "test@example.com"], path)
    _run(["git", "config", "user.name", "Test"], path)
    with open(os.path.join(path, "README.md"), "w") as f:
        f.write("init\n")
    _run(["git", "add", "."], path)
    _run(["git", "commit", "-m", "init"], path)


def add_worktree(repo_path: str, worktree_path: str, branch: str) -> None:
    """repo_path から新規ブランチ branch の worktree を worktree_path に作る。"""
    _run(["git", "worktree", "add", "-b", branch, worktree_path], repo_path)


class GitDestructiveBlockerTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gdb_test_")
        self.repo = os.path.join(self.tmpdir, "repo")
        os.makedirs(self.repo)
        init_repo(self.repo, "main")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- 回帰: cwd = 保護ブランチ上のリポ（-C/cd を含まない従来ケース） ---
    def test_commit_on_protected_branch_blocked(self):
        self.assertEqual(run_hook("git commit -m x", self.repo), 2)

    def test_push_on_protected_branch_blocked(self):
        self.assertEqual(run_hook("git push", self.repo), 2)

    def test_force_push_to_protected_branch_blocked(self):
        self.assertEqual(run_hook("git push --force origin main", self.repo), 2)

    def test_reset_hard_with_unpushed_commits_blocked(self):
        remote = os.path.join(self.tmpdir, "remote.git")
        _run(["git", "init", "--bare", "-b", "main", remote], self.tmpdir)
        _run(["git", "remote", "add", "origin", remote], self.repo)
        _run(["git", "push", "-u", "origin", "main"], self.repo)
        with open(os.path.join(self.repo, "a.txt"), "w") as f:
            f.write("a\n")
        _run(["git", "add", "."], self.repo)
        _run(["git", "commit", "-m", "unpushed"], self.repo)
        self.assertEqual(run_hook("git reset --hard HEAD~1", self.repo), 2)

    def test_clean_fd_blocked(self):
        self.assertEqual(run_hook("git clean -fd", self.repo), 2)

    def test_status_allowed(self):
        self.assertEqual(run_hook("git status", self.repo), 0)

    def test_push_on_non_protected_branch_allowed(self):
        _run(["git", "checkout", "-b", "feature/x"], self.repo)
        self.assertEqual(run_hook("git push", self.repo), 0)

    # --- 本丸: cd / -C で別ディレクトリに移ってから git を実行するケース ---
    def test_cd_to_feature_worktree_before_push_allowed(self):
        worktree = os.path.join(self.tmpdir, "wt-feat")
        add_worktree(self.repo, worktree, "feat")
        # hook プロセスの cwd は保護ブランチ(main)のリポのままにする
        exit_code = run_hook(f"cd {worktree} && git push -u origin feat", self.repo)
        self.assertEqual(exit_code, 0)

    def test_git_dash_c_to_feature_worktree_push_allowed(self):
        worktree = os.path.join(self.tmpdir, "wt-feat2")
        add_worktree(self.repo, worktree, "feat2")
        exit_code = run_hook(f"git -C {worktree} push", self.repo)
        self.assertEqual(exit_code, 0)

    def test_git_dash_c_to_protected_dir_blocked_even_from_nonprotected_cwd(self):
        # cwd 自体は非保護ブランチのチェックアウトだが、-C の指す先(self.repo)は
        # 保護ブランチ(main)。-C 先のブランチが正しく評価されればブロックされる
        # （cwd 側の branch だけ見ていたら誤って許可してしまう）。
        worktree = os.path.join(self.tmpdir, "wt-nonprotected")
        add_worktree(self.repo, worktree, "featC")
        exit_code = run_hook(f"git -C {self.repo} push", worktree)
        self.assertEqual(exit_code, 2)

    # --- パース規則 ---
    def test_cd_after_git_invocation_not_adopted_falls_back_to_cwd(self):
        # git push より後ろにある cd は採用しない -> cwd(=保護ブランチ)判定にフォールバック
        worktree = os.path.join(self.tmpdir, "wt-after")
        add_worktree(self.repo, worktree, "after")
        exit_code = run_hook(f"git push && cd {worktree}", self.repo)
        self.assertEqual(exit_code, 2)

    def test_last_cd_before_git_is_adopted(self):
        # A(=self.repo, protected な main) -> B(=非protectedブランチの worktree) の順に
        # cd してから push。採用されるのが最後の cd(B) であれば許可(exit 0)、
        # 最初の cd(A) やフォールバック cwd(=A) が使われていれば誤ってブロックされる(exit 2)。
        worktree_b = os.path.join(self.tmpdir, "wt-b")
        add_worktree(self.repo, worktree_b, "featB")
        exit_code = run_hook(f"cd {self.repo} && cd {worktree_b} && git push", self.repo)
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
