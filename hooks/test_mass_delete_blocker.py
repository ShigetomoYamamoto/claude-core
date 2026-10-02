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


class CommandEffectsMassDeleteTest(unittest.TestCase):
    """_command_effects.py 由来の検出(ADR-028)の契約テスト。

    - インタプリタ経由の削除(python3 -c "os.remove(...)" 等)を ask で捕捉すること。
    - sh -c に隠れた rm -r も ask で捕捉すること。
    - パス1(破滅的ターゲット判定)はトークン解析のみに留め、grep 等の文字列一致では
      deny されないこと(誤ブロックを避ける・ADR-028)。
    """

    def test_c01_python_inline_os_remove_asks(self):
        proc = run_hook_full('python3 -c "import os; os.remove(\'a\')"', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_c02_python_inline_shutil_rmtree_asks(self):
        proc = run_hook_full('python3 -c "import shutil; shutil.rmtree(\'build\')"', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_c03_node_inline_fs_rmsync_asks(self):
        proc = run_hook_full("node -e \"fs.rmSync('x', {recursive:true})\"", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_c04_sh_c_hidden_rm_rf_asks(self):
        proc = run_hook_full('sh -c "rm -rf /tmp/foo"', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_c05_python_inline_no_delete_api_passthrough(self):
        proc = run_hook_full("python3 -c \"print('hello')\"", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_c06_grep_mentioning_os_remove_not_interpreter_call(self):
        proc = run_hook_full('grep -n "os.remove" app.py', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_c07_grep_string_containing_rm_rf_not_denied(self):
        proc = run_hook_full('grep "rm -rf /" logfile', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)


class ExpandedHomePathMassDeleteTest(unittest.TestCase):
    """展開済みホーム絶対パス(/Users/<user> 等)への rm -rf も破滅的ターゲットとして
    決定的ブロック(exit 2)されることの契約テスト。

    既存バグ: is_catastrophic() は `~` / `$HOME` / `${HOME}` というリテラルの
    トークンしか見ておらず、単一階層絶対パス判定 `^/[^/]+/?\\*?$` も2セグメント以上の
    `/Users/<user>` を捕捉しない。結果、展開済み絶対パスで書かれたホーム削除が
    ask 止まりになっていた。ホームパスはハードコードせず実行環境の実際の値から組み立てる。
    """

    HOME = os.path.realpath(os.path.expanduser("~"))

    # --- 破滅的ターゲット: 即ブロック(exit 2) ---

    def test_e01_rm_rf_expanded_home_denied(self):
        proc = run_hook_full(f"rm -rf {self.HOME}", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e02_rm_rf_expanded_home_trailing_slash_denied(self):
        proc = run_hook_full(f"rm -rf {self.HOME}/", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e03_rm_rf_expanded_home_glob_denied(self):
        proc = run_hook_full(f"rm -rf {self.HOME}/*", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e04_rm_rf_quoted_expanded_home_denied(self):
        proc = run_hook_full(f'rm -rf "{self.HOME}"', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e05_rm_rf_dot_with_cwd_home_denied(self):
        # 相対指定(`.`)でも cwd がホームなら展開後にホームへ到達する。
        proc = run_hook_full("rm -rf .", self.HOME)
        self.assertEqual(proc.returncode, 2)

    def test_e06_rm_rf_dotdot_dotdot_reaches_home_parent_denied(self):
        # cwd = <HOME>/a/b から ../.. で /Users(単一階層の絶対パス)へ到達する。
        nested_cwd = os.path.join(self.HOME, "a", "b")
        proc = run_hook_full("rm -rf ../..", nested_cwd)
        self.assertEqual(proc.returncode, 2)

    # --- 既存の回帰: リテラルの ~ / $HOME / / / /usr は従来どおりブロックされ続ける ---

    def test_e07_regression_rm_rf_root_denied(self):
        proc = run_hook_full("rm -rf /", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e08_regression_rm_rf_tilde_denied(self):
        proc = run_hook_full("rm -rf ~", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e09_regression_rm_rf_home_env_denied(self):
        proc = run_hook_full("rm -rf $HOME", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_e10_regression_rm_rf_usr_denied(self):
        proc = run_hook_full("rm -rf /usr", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    # --- ホーム直下の個別ディレクトリ・許可リストは対象外(ask または素通り。exit 2 でないこと) ---

    def test_e11_rm_rf_home_downloads_not_denied(self):
        proc = run_hook_full(f"rm -rf {self.HOME}/Downloads", DEFAULT_CWD)
        self.assertNotEqual(proc.returncode, 2)

    def test_e12_rm_rf_home_nested_project_build_not_denied(self):
        proc = run_hook_full(f"rm -rf {self.HOME}/dotfiles/claude-core/build", DEFAULT_CWD)
        self.assertNotEqual(proc.returncode, 2)

    def test_e13_rm_rf_node_modules_in_home_proj_allowed_silently(self):
        proc = run_hook_full("rm -rf node_modules", os.path.join(self.HOME, "proj"))
        self.assertNotEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")

    def test_e14_rm_rf_build_in_home_proj_allowed_silently(self):
        proc = run_hook_full("rm -rf build", os.path.join(self.HOME, "proj"))
        self.assertNotEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")

    def test_e15_ls_passthrough(self):
        proc = run_hook_full("ls -la", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")


class FindXargsMassDeleteTest(unittest.TestCase):
    """find / xargs 経由の削除の検出(find -delete / -exec rm / xargs rm)の契約テスト。

    - find の起点が破滅的(/ , ~ , $HOME , 展開済みホーム)なら deny(パス1と同様、素の解析のみ)。
    - 起点が全て再生成可能なら ask を省略、それ以外は ask。
    - xargs rm は対象が stdin で判定できないため常に ask。
    - sh -c に隠れた形は ask のみ(deny しない)。
    """

    HOME = os.path.realpath(os.path.expanduser("~"))
    SCRATCH = "/private/tmp/claude-x/y/scratchpad"

    def assert_ask(self, command, cwd=DEFAULT_CWD):
        proc = run_hook_full(command, cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def assert_deny(self, command, cwd=DEFAULT_CWD):
        proc = run_hook_full(command, cwd)
        self.assertEqual(proc.returncode, 2, proc.stdout)

    def assert_silent(self, command, cwd=DEFAULT_CWD):
        proc = run_hook_full(command, cwd)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- deny ---
    def test_f01_find_home_delete_denied(self):
        self.assert_deny("find ~ -delete")

    def test_f02_find_root_name_delete_denied(self):
        self.assert_deny("find / -name '*.bak' -delete")

    def test_f03_find_home_env_exec_rm_denied(self):
        self.assert_deny("find $HOME -type f -exec rm {} +")

    def test_f04_find_expanded_home_delete_denied(self):
        self.assert_deny(f"find {os.path.expanduser('~')} -delete")

    def test_f05_find_home_exec_rm_rf_denied(self):
        self.assert_deny("find ~ -exec rm -rf {} +")

    # --- ask ---
    def test_f10_find_dot_type_f_delete_asks(self):
        self.assert_ask("find . -type f -delete")

    def test_f11_find_src_delete_asks(self):
        self.assert_ask("find src -name '*.log' -delete")

    def test_f12_find_exec_rm_plus_asks(self):
        self.assert_ask("find . -name '*.log' -exec rm {} +")

    def test_f13_find_exec_rm_semicolon_asks(self):
        self.assert_ask("find . -exec rm {} \\;")

    def test_f14_ls_xargs_rm_asks(self):
        self.assert_ask("ls | xargs rm")

    def test_f15_find_home_pipe_xargs_rm_asks(self):
        self.assert_ask("find ~ -type f | xargs rm")

    def test_f16_xargs_0_rm_asks(self):
        self.assert_ask("xargs -0 rm")

    def test_f17_xargs_I_rm_asks(self):
        self.assert_ask("xargs -I {} rm {}")

    def test_f18_xargs_n_1_rm_f_asks(self):
        self.assert_ask("xargs -n 1 rm -f")

    def test_f19_sh_c_find_delete_asks(self):
        self.assert_ask('sh -c "find . -delete"')

    def test_f20_find_home_downloads_delete_asks(self):
        self.assert_ask("find ~/Downloads -delete")

    # --- 無反応 ---
    def test_f30_find_without_delete_passthrough(self):
        self.assert_silent("find . -name '*.log'")

    def test_f31_find_node_modules_delete_silent(self):
        self.assert_silent("find node_modules -delete")

    def test_f32_find_dot_delete_in_scratchpad_silent(self):
        self.assert_silent("find . -delete", cwd=self.SCRATCH)

    def test_f33_xargs_grep_passthrough(self):
        self.assert_silent("ls | xargs grep foo")

    def test_f34_xargs_cp_passthrough(self):
        self.assert_silent("xargs -I {} cp {} dst")

    def test_f35_git_log_passthrough(self):
        self.assert_silent("git log --oneline")


class UnlinkShredRsyncMassDeleteTest(unittest.TestCase):
    """unlink / rmdir / shred / rsync --delete / Perl 括弧なし unlink の検出の契約テスト(#109)。

    - unlink / rmdir: ask。対象が全て再生成可能なら省略。shred: 常に ask。
    - rsync: delete 系オプションがあるときだけ対象。宛先が破滅的なら deny、再生成可能なら通過、
      それ以外は ask。dry-run は対象外。リモート宛先は ask(パスが破滅的なら deny)。
    - sh -c に隠れた形は ask のみ(deny しない)。
    """

    HOME = os.path.realpath(os.path.expanduser("~"))

    def assert_ask(self, command, cwd=DEFAULT_CWD):
        proc = run_hook_full(command, cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def assert_deny(self, command, cwd=DEFAULT_CWD):
        proc = run_hook_full(command, cwd)
        self.assertEqual(proc.returncode, 2, proc.stdout)

    def assert_silent(self, command, cwd=DEFAULT_CWD):
        proc = run_hook_full(command, cwd)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    # --- unlink / rmdir / shred ---
    def test_u01_unlink_asks(self):
        self.assert_ask("unlink notes.txt")

    def test_u02_rmdir_asks(self):
        self.assert_ask("rmdir src/old")

    def test_u03_unlink_safe_target_silent(self):
        self.assert_silent("unlink dist/x.js")

    def test_u04_rmdir_safe_target_silent(self):
        self.assert_silent("rmdir node_modules/.cache")

    def test_u05_shred_u_asks(self):
        self.assert_ask("shred -u secret.txt")

    def test_u06_shred_plain_asks(self):
        self.assert_ask("shred file")

    def test_u07_shred_safe_target_still_asks(self):
        self.assert_ask("shred -u dist/a")

    # --- rsync --delete: deny ---
    def test_u10_rsync_delete_home_tilde_denied(self):
        self.assert_deny("rsync -a --delete src/ ~/")

    def test_u11_rsync_delete_expanded_home_denied(self):
        self.assert_deny(f"rsync -a --delete src/ {self.HOME}/")

    def test_u12_rsync_delete_root_denied(self):
        self.assert_deny("rsync -a --delete empty/ /")

    def test_u13_rsync_delete_remote_root_denied(self):
        self.assert_deny("rsync -a --delete src/ server:/")

    # --- rsync --delete: ask ---
    def test_u20_rsync_delete_local_asks(self):
        self.assert_ask("rsync -a --delete src/ backup/")

    def test_u21_rsync_delete_after_asks(self):
        self.assert_ask("rsync -av --delete-after src/ backup/")

    def test_u22_rsync_del_asks(self):
        self.assert_ask("rsync -a --del src/ backup/")

    def test_u23_rsync_delete_remote_asks(self):
        self.assert_ask("rsync -a --delete src/ server:/srv/app")

    # --- rsync: 通過 ---
    def test_u30_rsync_delete_short_dry_run_silent(self):
        self.assert_silent("rsync -avn --delete src/ backup/")

    def test_u31_rsync_delete_long_dry_run_silent(self):
        self.assert_silent("rsync -a --dry-run --delete src/ backup/")

    def test_u32_rsync_delete_safe_dest_silent(self):
        self.assert_silent("rsync -a --delete src/ node_modules/")

    def test_u33_rsync_without_delete_silent(self):
        self.assert_silent("rsync -a src/ backup/")

    # --- Perl 括弧なし unlink ---
    def test_u40_perl_unlink_string_asks(self):
        self.assert_ask("perl -e \"unlink 'a'\"")

    def test_u41_perl_unlink_array_asks(self):
        self.assert_ask("perl -e 'unlink @files'")

    def test_u42_grep_unlink_silent(self):
        self.assert_silent("grep -rn unlink src/")

    # --- sh -c に隠れた形(ask のみ) ---
    def test_u50_sh_c_shred_asks(self):
        self.assert_ask('sh -c "shred -u x"')

    def test_u51_sh_c_rsync_delete_home_asks_not_denied(self):
        self.assert_ask('sh -c "rsync -a --delete a/ ~/"')

    # --- 素通りの確認 ---
    def test_u60_echo_unlink_silent(self):
        self.assert_silent("echo unlink")

    def test_u61_ls_rsync_notes_silent(self):
        self.assert_silent("ls rsync-notes/")

    # --- シェル構文の直後(コマンド位置) ---
    def test_u70_for_loop_unlink_asks(self):
        self.assert_ask('for f in *; do unlink "$f"; done')

    def test_u71_if_then_shred_asks(self):
        self.assert_ask("if [ -f a ]; then shred -u a; fi")

    def test_u72_subshell_unlink_asks(self):
        self.assert_ask("(unlink a)")

    def test_u73_grep_shred_silent(self):
        self.assert_silent("grep -rn shred src/")

    # --- find -exec / xargs が unlink / rmdir / shred を実行 ---
    def test_u80_find_exec_unlink_asks(self):
        self.assert_ask("find . -exec unlink {} \\;")

    def test_u81_find_home_exec_shred_denied(self):
        self.assert_deny("find ~ -exec shred -u {} +")

    def test_u82_find_safe_exec_unlink_silent(self):
        self.assert_silent("find node_modules -exec unlink {} \\;")

    def test_u83_xargs_unlink_asks(self):
        self.assert_ask("ls | xargs unlink")

    def test_u84_xargs_shred_asks(self):
        self.assert_ask("xargs shred -u < list")

    # --- unlink の祖先ルールは cwd 配下のみ ---
    def test_u90_unlink_under_safe_dir_in_cwd_silent(self):
        self.assert_silent("unlink dist/x.js", cwd=DEFAULT_CWD)

    def test_u91_unlink_parent_relative_asks(self):
        self.assert_ask("unlink ../dist/x.js", cwd=DEFAULT_CWD)

    def test_u92_unlink_outside_cwd_with_safe_ancestor_asks(self):
        self.assert_ask(f"unlink {self.HOME}/work-out-test/out/proj/src/a.py", cwd=DEFAULT_CWD)

    # --- rsync: オプション値は宛先ではない ---
    def test_u100_rsync_exclude_value_not_dest_asks(self):
        self.assert_ask("rsync -a --delete src/ backup/ --exclude node_modules")

    def test_u101_rsync_exclude_value_home_dest_denied(self):
        self.assert_deny("rsync -a --delete src/ ~/ --exclude node_modules")

    def test_u102_rsync_e_ssh_home_dest_denied(self):
        self.assert_deny("rsync -a --delete -e ssh src/ ~/")

    def test_u103_rsync_exclude_eq_safe_dest_silent(self):
        self.assert_silent("rsync -a --delete --exclude=node_modules src/ node_modules/")


class CommandEffectsModuleMissingMassDeleteTest(unittest.TestCase):
    """_command_effects.py が import できない環境でも、mass-delete-blocker は
    従来どおりの rm トークン解析だけで動き続けることを確認する(ADR-028)。

    HOOK 単体を _command_effects.py のない一時ディレクトリへコピーして起動する
    (元ディレクトリの hooks/__pycache__ は巻き込まない)。
    """

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="mdb_no_effects_")
        self._copied_hook = os.path.join(self._tmpdir, "mass-delete-blocker.py")
        shutil.copy(HOOK, self._copied_hook)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def run_copied_hook(self, command: str, cwd: str) -> subprocess.CompletedProcess:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
        return subprocess.run(
            ["python3", self._copied_hook],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )

    def test_01_degraded_rm_rf_root_still_denied(self):
        proc = self.run_copied_hook("rm -rf /", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 2)

    def test_02_degraded_ls_still_passthrough(self):
        proc = self.run_copied_hook("ls", DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)

    # --- 劣化の裏取り: フォールバックが効いていなければ ask されるはずの入力が無反応になること ---
    def test_03_degraded_python_inline_os_remove_not_detected(self):
        proc = self.run_copied_hook('python3 -c "import os; os.remove(\'a\')"', DEFAULT_CWD)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
