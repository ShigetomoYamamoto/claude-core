#!/usr/bin/env python3
"""opus-execution-guard.py の契約テスト（stdlib unittest・依存追加なし）。

実行: python3 -m unittest hooks/test_opus_execution_guard.py
      （または python3 hooks/test_opus_execution_guard.py）

hook は PreToolUse で stdin から JSON を受け取り、
メインループ(agent_id なし)が Edit/Write/MultiEdit/NotebookEdit または
変更系 Bash を実行しようとした場合に exit 2 でブロックする(ADR-026)。
判定軸は agent_id の有無のみで、モデルは一切見ない。
例外は auto-memory(~/.claude/projects/*/memory/)とセッション scratchpad の
固定パス2箇所のみ。サブエージェント(agent_id あり)・監視対象外ツールは通過させる。
"""
import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opus-execution-guard.py")


def write_transcript(records: list) -> str:
    """records を JSONL で一時ファイルに書き path を返す。
    各要素は dict(通常) または str(壊れた行の注入用)を受け付ける。
    """
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="transcript_test_")
    with os.fdopen(fd, "w") as f:
        for rec in records:
            if isinstance(rec, str):
                f.write(rec + "\n")
            else:
                f.write(json.dumps(rec) + "\n")
    return path


def run_hook(tool_name: str, tool_input: dict, transcript_path: str, agent_id=None) -> int:
    """payload を組んで hook を subprocess 起動し returncode を返す。"""
    return run_hook_full(tool_name, tool_input, transcript_path, agent_id).returncode


def run_hook_full(tool_name: str, tool_input: dict, transcript_path: str, agent_id=None):
    """payload を組んで hook を subprocess 起動し CompletedProcess を返す(stderr も参照可)。"""
    payload: dict = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "transcript_path": transcript_path,
    }
    if agent_id is not None:
        payload["agent_id"] = agent_id
    return subprocess.run(
        ["python3", HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def opus_assistant(model: str = "claude-opus-4-8") -> dict:
    """直近 assistant レコードのひな型(model はもう読まれないが引数として渡し続けてよい)。"""
    return {"type": "assistant", "message": {"model": model}}


def user_msg() -> dict:
    return {"type": "user", "message": {"content": "hello"}}


class OpusExecutionGuardTest(unittest.TestCase):

    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    def make_transcript(self, records: list) -> str:
        path = write_transcript(records)
        self._paths.append(path)
        return path

    def memory_path(self) -> str:
        """auto-memory の許可パス例を組む(実行環境依存を避けるため expanduser を使う)。"""
        return os.path.join(
            os.path.expanduser("~"), ".claude", "projects", "some-project",
            "memory", "a.md",
        )

    # --- ケース1: メイン(agent_id なし) + Edit → ブロック ---
    def test_01_main_edit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース2: メイン + Write → ブロック ---
    def test_02_main_write_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Write", {"file_path": "/tmp/x.py", "content": "x"}, t), 2)

    # --- ケース3: メイン + MultiEdit → ブロック ---
    def test_03_main_multiedit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("MultiEdit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース4: メイン + NotebookEdit → ブロック ---
    def test_04_main_notebookedit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("NotebookEdit", {"notebook_path": "/tmp/x.ipynb"}, t), 2)

    # --- ケース5: model が sonnet でもメインなら Edit はブロック(モデル非依存) ---
    def test_05_sonnet_main_edit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-sonnet-4-6")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース6: model が haiku でもメインなら Edit はブロック(モデル非依存) ---
    def test_06_haiku_main_edit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-haiku-4-5-20251001")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース7: model が opus でもメインなら Edit はブロック(モデル非依存) ---
    def test_07_opus_main_edit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース8: model が判定不能(空 transcript)でもメインなら Edit はブロック ---
    def test_08_no_model_main_edit_still_blocked(self):
        t = self.make_transcript([])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース9: transcript_path が存在しなくてもメインなら Edit はブロック ---
    def test_09_nonexistent_transcript_main_edit_still_blocked(self):
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, "/nonexistent/path/transcript.jsonl"), 2)

    # --- ケース10: メイン + Edit、パスが memory 配下 → 通過 ---
    def test_10_main_edit_memory_path_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": self.memory_path()}, t), 0)

    # --- ケース11: メイン + Write、パスが /private/tmp scratchpad 配下 → 通過 ---
    def test_11_main_write_private_tmp_scratchpad_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        p = "/private/tmp/claude-501/-some-project/abcd1234/scratchpad/x.txt"
        self.assertEqual(run_hook("Write", {"file_path": p, "content": "x"}, t), 0)

    # --- ケース12: メイン + Write、パスが /tmp scratchpad 配下 → 通過 ---
    def test_12_main_write_tmp_scratchpad_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        p = "/tmp/claude-501/-some-project/abcd1234/scratchpad/x.txt"
        self.assertEqual(run_hook("Write", {"file_path": p, "content": "x"}, t), 0)

    # --- ケース13: メイン + Edit、file_path が空 → fail-open で通過 ---
    def test_13_main_edit_empty_path_fail_open(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": ""}, t), 0)

    # --- ケース14: メイン + Edit、file_path も notebook_path も欠落 → fail-open で通過 ---
    def test_14_main_edit_missing_path_fail_open(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {}, t), 0)

    # --- ケース15: サブエージェント(agent_id あり) + Edit、任意のパス → 通過 ---
    def test_15_subagent_edit_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t, agent_id="agent-abc123"), 0)

    # --- ケース16: サブエージェント + Bash rm -rf → 通過 ---
    def test_16_subagent_bash_rm_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "rm -rf x"}, t, agent_id="agent-abc123"), 0)

    # --- ケース17: メイン + Bash rm -rf → ブロック ---
    def test_17_main_bash_rm_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "rm -rf build"}, t), 2)

    # --- ケース18: メイン + Bash git commit → ブロック ---
    def test_18_main_bash_git_commit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "git commit -m x"}, t), 2)

    # --- ケース19: メイン + Bash sed -i → ブロック ---
    def test_19_main_bash_sed_inplace_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "sed -i 's/a/b/' f"}, t), 2)

    # --- ケース20: メイン + Bash mkdir → ブロック ---
    def test_20_main_bash_mkdir_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "mkdir foo"}, t), 2)

    # --- ケース21: メイン + Bash npm install → ブロック ---
    def test_21_main_bash_npm_install_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "npm install"}, t), 2)

    # --- ケース22: メイン + Bash リダイレクト > → ブロック ---
    def test_22_main_bash_redirect_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "echo x > out.txt"}, t), 2)

    # --- ケース23: メイン + Bash リダイレクト 1> → ブロック ---
    def test_23_main_bash_fd_redirect_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "echo hi 1> out.txt"}, t), 2)

    # --- ケース24: メイン + Bash git status → 通過 ---
    def test_24_main_bash_git_status_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "git status"}, t), 0)

    # --- ケース25: メイン + Bash ls -la → 通過 ---
    def test_25_main_bash_ls_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "ls -la"}, t), 0)

    # --- ケース26: メイン + Bash npm test → 通過 ---
    def test_26_main_bash_npm_test_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "npm test"}, t), 0)

    # --- ケース27: メイン + Bash pytest -q → 通過 ---
    def test_27_main_bash_pytest_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "pytest -q"}, t), 0)

    # --- ケース28: メイン + Bash git log --grep 引数内の rm は誤爆しない ---
    def test_28_main_bash_rm_in_arg_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": 'git log --grep "rm -rf"'}, t), 0)

    # --- ケース29: メイン + Bash echo 文字列内の rm は誤爆しない ---
    def test_29_main_bash_rm_in_string_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": 'echo "rm me"'}, t), 0)

    # --- ケース30: メイン + Bash 引用符内の -> は誤検知しない(読み取り専用) ---
    def test_30_main_bash_arrow_in_quotes_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": 'grep -n "a->b" f.txt'}, t), 0)

    # --- ケース31: メイン + Bash 引用符内の >= は誤検知しない(読み取り専用) ---
    def test_31_main_bash_gte_in_quotes_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "awk 'NR>=600 && NR<=620' f.txt"}, t), 0)

    # --- ケース32: メイン + Bash 裸の => は誤検知しない ---
    def test_32_main_bash_fat_arrow_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "echo x=>y"}, t), 0)

    # --- ケース33: メイン + Bash fd 複製 2>&1 は通過 ---
    def test_33_main_bash_fd_dup_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "ls -la 2>&1"}, t), 0)

    # --- ケース34: メイン + Bash 2>/dev/null は通過(頻出する読み取り専用の書き方) ---
    def test_34_main_bash_stderr_to_devnull_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "find . -name x 2>/dev/null"}, t), 0)

    # --- ケース35: メイン + Bash > /dev/null は通過 ---
    def test_35_main_bash_stdout_to_devnull_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "make build > /dev/null"}, t), 0)

    # --- ケース36: メイン + Bash >> /dev/null は通過 ---
    def test_36_main_bash_append_to_devnull_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "make build >> /dev/null"}, t), 0)

    # --- ケース37: メイン + Bash /dev/null に似た別ファイルはブロック ---
    def test_37_main_bash_devnull_lookalike_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "echo x > /dev/nullish"}, t), 2)

    # --- ケース38: 監視対象外ツール(Read) → 即通過 ---
    def test_38_non_monitored_tool_passthrough(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Read", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース39: ブロック時 stderr に案内メッセージが出る(stdout は空) ---
    def test_39_block_outputs_to_stderr_not_stdout(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        proc = run_hook_full("Edit", {"file_path": "/tmp/x.py"}, t)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("メインループは実作業を担当しません", proc.stderr)
        self.assertEqual(proc.stdout, "")

    # --- ケース40: ブロック時のメッセージが委譲を案内し、思考ティア言及は含まない ---
    def test_40_block_message_content(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        proc = run_hook_full("Edit", {"file_path": "/tmp/x.py"}, t)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("run_in_background: false", proc.stderr)
        self.assertIn("ユーザーにモデル切り替えを依頼しないこと", proc.stderr)
        self.assertNotIn("思考ティア", proc.stderr)

    # --- ケース41: transcript にユーザ行が混ざっていてもメインの Edit は判定に影響しない ---
    def test_41_intervening_user_rows_do_not_affect_decision(self):
        records = [user_msg(), opus_assistant("claude-opus-4-8"), user_msg()]
        t = self.make_transcript(records)
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース42: 壊れた行を含む transcript でもメインの Edit はブロックされる(判定は agent_id のみ) ---
    def test_42_broken_transcript_lines_do_not_affect_decision(self):
        broken_line = '{"broken": true'   # 不完全 JSON
        t = self.make_transcript([broken_line, opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース43: メイン + Bash 引用符内の | 交替パターンに削除語が含まれるだけ → 通過(読み取り専用) ---
    def test_43_main_bash_quoted_pipe_with_denylisted_word_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        cmd = 'grep -n "REMOVE\\|stale\\|unlink" installer.py'
        self.assertEqual(run_hook("Bash", {"command": cmd}, t), 0)

    # --- ケース44: メイン + Bash 引用符内の | に cp/mv が含まれるだけ → 通過(読み取り専用) ---
    def test_44_main_bash_quoted_pipe_with_copy_move_words_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        cmd = 'grep "cp\\|mv" f'
        self.assertEqual(run_hook("Bash", {"command": cmd}, t), 0)

    # --- ケース45: メイン + Bash 引用符内の ; に mkdir が続くだけ → 通過(読み取り専用) ---
    def test_45_main_bash_quoted_semicolon_with_mkdir_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        cmd = 'echo "foo;mkdir bar"'
        self.assertEqual(run_hook("Bash", {"command": cmd}, t), 0)

    # --- ケース46: 既知の検出漏れ — 引用符内サブシェル(sh -c "...; rm -rf x")の破壊操作は検出できない ---
    # これは is_mutating_bash のコメントに明記した意図的な代償であり、バグではない。
    # クォート内を空白に置換してから判定するため、引用符の中に隠れた ; rm -rf は見えなくなる。
    # 検出漏れを許容する代わりに grep "cp\|mv" 等の誤検知を減らす選択をしたため(ADR-006 の
    # fail-open と同じ判断)。将来 sh -c 経由のコマンドインジェクションに対応する場合は
    # このテストの期待値を更新すること。
    def test_46_known_gap_quoted_subshell_mutation_not_detected(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        cmd = 'sh -c "foo; rm -rf /tmp/x"'
        self.assertEqual(run_hook("Bash", {"command": cmd}, t), 0)

    # --- ケース47: 引用符の外にある本物の破壊操作は引き続きブロックされる ---
    def test_47_unquoted_mutation_still_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        cmd = 'ls; rm -rf build'
        self.assertEqual(run_hook("Bash", {"command": cmd}, t), 2)


if __name__ == "__main__":
    unittest.main()
