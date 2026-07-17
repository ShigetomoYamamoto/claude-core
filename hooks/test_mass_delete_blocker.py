#!/usr/bin/env python3
"""mass-delete-blocker.py の契約テスト(stdlib unittest・依存追加なし)。

実行: python3 -m unittest hooks/test_mass_delete_blocker.py
      (または python3 hooks/test_mass_delete_blocker.py)

hook は PreToolUse で stdin から JSON を受け取り、
- 破滅的ターゲット(/ , ~ , $HOME , /usr のような単一階層の絶対パス等)への
  再帰削除(rm -r 系)を exit 2 で即ブロックする(パス1)。
- それ以外の再帰削除・THRESHOLD 件以上のワイルドカード削除は permissionDecision="ask" を返す
  (パス2/3)。ただし対象が SAFE_BASENAMES / セッション scratchpad / $TMPDIR 配下のみで
  構成される場合は ask を省略する(再生成可能な許可リストの緩和)。
- rm を含まないコマンドは無反応で通過する。
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mass-delete-blocker.py")

# 大半のテストで使う「安全リストにも TMPDIR にも該当しない」既定 cwd(このリポジトリのルート)。
DEFAULT_CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_hook_full(command: str, cwd: str, extra_env: dict = None, proc_cwd: str = None):
    """payload を組んで hook を subprocess 起動し CompletedProcess を返す。

    cwd: stdin JSON の "cwd" フィールド(hook 内のパス展開に使われる)。
    proc_cwd: 実際に subprocess を起動する OS 上の cwd(glob.glob の挙動に使われる)。
              未指定なら現在のプロセスの cwd のまま(Python の subprocess 既定)。
    """
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": cwd,
    }
    run_env = os.environ.copy()
    if extra_env:
        run_env.update(extra_env)
    return subprocess.run(
        ["python3", HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=run_env,
        cwd=proc_cwd,
    )


def run_hook(command: str, cwd: str, extra_env: dict = None, proc_cwd: str = None) -> int:
    return run_hook_full(command, cwd, extra_env, proc_cwd).returncode


class MassDeleteBlockerTest(unittest.TestCase):

    # --- ケース1: rm -rf / → 破滅的ターゲット、即ブロック ---
    def test_01_rm_rf_root_denied(self):
        proc = run_hook_full("rm -rf /", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    # --- ケース2: rm -rf ~ → 破滅的ターゲット、即ブロック ---
    def test_02_rm_rf_tilde_denied(self):
        proc = run_hook_full("rm -rf ~", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    # --- ケース3: rm -rf /usr → 単一階層の絶対パス、即ブロック ---
    def test_03_rm_rf_usr_denied(self):
        proc = run_hook_full("rm -rf /usr", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    # --- ケース4: rm -rf src → 許可リスト外、ask ---
    def test_04_rm_rf_src_asks(self):
        proc = run_hook_full("rm -rf src", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "ask"
        )

    # --- ケース5: rm -rf node_modules → 許可リスト、ask なしで通過 ---
    def test_05_rm_rf_node_modules_allowed_silently(self):
        proc = run_hook_full("rm -rf node_modules", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- ケース6: 複数ターゲットとも許可リスト(ネストパスの basename も判定) → ask なし ---
    def test_06_rm_rf_multiple_safe_targets_allowed_silently(self):
        proc = run_hook_full("rm -rf packages/foo/node_modules dist", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- ケース7: 許可リストと非許可の混在 → ask(全ターゲットが安全でないと通さない) ---
    def test_07_rm_rf_mixed_safe_and_unsafe_asks(self):
        proc = run_hook_full("rm -rf node_modules src", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "ask"
        )

    # --- ケース8: セッション scratchpad(/private/tmp/claude-*) 配下 → ask なし ---
    def test_08_rm_rf_session_scratchpad_allowed_silently(self):
        proc = run_hook_full("rm -rf /private/tmp/claude-501/x/y", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- ケース9: $TMPDIR 配下(サブプロセス env に TMPDIR を設定) → ask なし ---
    def test_09_rm_rf_tmpdir_env_allowed_silently(self):
        tmpdir = tempfile.mkdtemp(prefix="mdb_tmpdir_test_")
        try:
            proc = run_hook_full(
                "rm -rf $TMPDIR/foo", DEFAULT_CWD, extra_env={"TMPDIR": tmpdir}
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout, "")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # --- ケース10: rm -rf dist/* → glob 記号を含む basename は親ディレクトリ名で判定 → ask なし ---
    def test_10_rm_rf_dist_glob_allowed_silently(self):
        proc = run_hook_full("rm -rf dist/*", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- ケース11: rm -rf tmp → 許可リスト、ask なし ---
    def test_11_rm_rf_tmp_allowed_silently(self):
        proc = run_hook_full("rm -rf tmp", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- ケース12: 非再帰でも許可リスト外のワイルドカード大量削除は ask ---
    def test_12_wildcard_mass_delete_non_safe_dir_still_asks(self):
        fixture_dir = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
        try:
            for i in range(12):
                with open(os.path.join(fixture_dir, f"f{i}.log"), "w") as f:
                    f.write("x")
            proc = run_hook_full("rm *.log", fixture_dir, proc_cwd=fixture_dir)
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertEqual(
                out["hookSpecificOutput"]["permissionDecision"], "ask"
            )
        finally:
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # --- ケース13: rm を含まないコマンド → 無反応で通過 ---
    def test_13_non_rm_command_passthrough(self):
        proc = run_hook_full("ls -R /", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- ケース14: rm -rf "$HOME" → クォート付き環境変数ホームも破滅的、即ブロック ---
    def test_14_rm_rf_quoted_home_env_denied(self):
        proc = run_hook_full('rm -rf "$HOME"', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
