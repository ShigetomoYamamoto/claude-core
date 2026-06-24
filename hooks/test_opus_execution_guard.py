#!/usr/bin/env python3
"""opus-execution-guard.py の契約テスト（stdlib unittest・依存追加なし）。

実行: python3 -m unittest hooks/test_opus_execution_guard.py
      （または python3 hooks/test_opus_execution_guard.py）

hook は PreToolUse で stdin から JSON を受け取り、
メインループの Opus が Edit/Write/MultiEdit/NotebookEdit または
変更系 Bash を実行しようとした場合に exit 2 でブロックする。
サブエージェント(agent_id あり)・Sonnet/Haiku・監視対象外ツールは通過させる。
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
    """直近 assistant レコードのひな型。"""
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

    # --- ケース1: Opus + Edit → ブロック ---
    def test_01_opus_edit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース2: Opus 1M + Write → ブロック ---
    def test_02_opus_1m_write_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8[1m]")])
        self.assertEqual(run_hook("Write", {"file_path": "/tmp/x.py", "content": "x"}, t), 2)

    # --- ケース3: Opus + MultiEdit → ブロック ---
    def test_03_opus_multiedit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("MultiEdit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース4: Opus + NotebookEdit → ブロック ---
    def test_04_opus_notebookedit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("NotebookEdit", {"notebook_path": "/tmp/x.ipynb"}, t), 2)

    # --- ケース5: Sonnet + Edit → 通過 ---
    def test_05_sonnet_edit_allowed(self):
        t = self.make_transcript([opus_assistant("claude-sonnet-4-6")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース6: Haiku + Edit → 通過 ---
    def test_06_haiku_edit_allowed(self):
        t = self.make_transcript([opus_assistant("claude-haiku-4-5-20251001")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース7: Opus + Bash rm -rf → ブロック ---
    def test_07_opus_bash_rm_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "rm -rf build"}, t), 2)

    # --- ケース8: Opus + Bash git commit → ブロック ---
    def test_08_opus_bash_git_commit_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "git commit -m x"}, t), 2)

    # --- ケース9: Opus + Bash sed -i → ブロック ---
    def test_09_opus_bash_sed_inplace_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "sed -i 's/a/b/' f"}, t), 2)

    # --- ケース10: Opus + Bash mkdir → ブロック ---
    def test_10_opus_bash_mkdir_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "mkdir foo"}, t), 2)

    # --- ケース11: Opus + Bash npm install → ブロック ---
    def test_11_opus_bash_npm_install_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "npm install"}, t), 2)

    # --- ケース12: Opus + Bash リダイレクト > → ブロック ---
    def test_12_opus_bash_redirect_blocked(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "echo x > out.txt"}, t), 2)

    # --- ケース13: Opus + Bash git status → 通過 ---
    def test_13_opus_bash_git_status_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "git status"}, t), 0)

    # --- ケース14: Opus + Bash ls → 通過 ---
    def test_14_opus_bash_ls_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "ls -la"}, t), 0)

    # --- ケース15: Opus + Bash npm test → 通過 ---
    def test_15_opus_bash_npm_test_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "npm test"}, t), 0)

    # --- ケース16: Opus + Bash pytest → 通過 ---
    def test_16_opus_bash_pytest_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "pytest -q"}, t), 0)

    # --- ケース17: Opus + Bash git log --grep 引数内の rm は誤爆しない ---
    def test_17_opus_bash_rm_in_arg_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": 'git log --grep "rm -rf"'}, t), 0)

    # --- ケース18: Opus + Bash echo 文字列内の rm は誤爆しない ---
    def test_18_opus_bash_rm_in_string_no_false_positive(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": 'echo "rm me"'}, t), 0)

    # --- ケース19: assistant 行に model フィールドなし → fail-open ---
    def test_19_no_model_field_fail_open(self):
        t = self.make_transcript([{"type": "assistant", "message": {}}])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース20: 空 transcript → fail-open ---
    def test_20_empty_transcript_fail_open(self):
        t = self.make_transcript([])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース21: transcript_path が存在しないパス → fail-open ---
    def test_21_nonexistent_transcript_fail_open(self):
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, "/nonexistent/path/transcript.jsonl"), 0)

    # --- ケース22: 壊れた行を含む JSONL, 末尾に opus-assistant → ブロック ---
    def test_22_broken_lines_skipped_latest_opus_blocked(self):
        broken_line = '{"broken": true'   # 不完全 JSON
        t = self.make_transcript([broken_line, opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース23: user 行を挟む; 逆順で assistant を正しく拾う ---
    def test_23_intervening_user_rows_picks_latest_assistant(self):
        records = [user_msg(), opus_assistant("claude-opus-4-8"), user_msg()]
        t = self.make_transcript(records)
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 2)

    # --- ケース24: claude-sonnet-opusish-9 (前方一致厳密性) → 通過 ---
    def test_24_fake_opus_name_allowed(self):
        t = self.make_transcript([opus_assistant("claude-sonnet-opusish-9")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース25: Opus + Edit + agent_id あり → 通過 (サブエージェント) ---
    def test_25_subagent_edit_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Edit", {"file_path": "/tmp/x.py"}, t, agent_id="agent-abc123"), 0)

    # --- ケース26: Opus + Bash rm + agent_id あり → 通過 (サブエージェント) ---
    def test_26_subagent_bash_rm_allowed(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Bash", {"command": "rm -rf x"}, t, agent_id="agent-abc123"), 0)

    # --- ケース27: 監視対象外ツール(Read) → 即通過 ---
    def test_27_non_monitored_tool_passthrough(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        self.assertEqual(run_hook("Read", {"file_path": "/tmp/x.py"}, t), 0)

    # --- ケース28: ブロック時 stderr に案内メッセージが出る(stdout は空) ---
    def test_28_block_outputs_to_stderr_not_stdout(self):
        t = self.make_transcript([opus_assistant("claude-opus-4-8")])
        proc = run_hook_full("Edit", {"file_path": "/tmp/x.py"}, t)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Opus はファイル編集・変更系 Bash 操作を直接実行できません。", proc.stderr)
        self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
